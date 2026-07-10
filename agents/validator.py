"""
validator.py — Story Quality Validator Agent

Scores a story outline across 5 criteria (0–10 each).
Total >= 35 = PASS. Runs as a LangGraph node.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from langchain_openai import ChatOpenAI

from agents.state import AgentNote, ArcwrightState, ValidationResult

logger = logging.getLogger(__name__)

# ─── LLM ──────────────────────────────────────────────────────────────────────

def _get_llm() -> ChatOpenAI:
    """Lazy LLM init — avoids crash on import when API key not set."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

# ─── Prompt ───────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a ruthlessly honest story quality validator for short-form storytelling content.
Your job is to score a story concept on 5 criteria, each out of 10.

Criteria:
1. Relatability      — Will the target audience see themselves in this story?
2. Emotional Hook    — Does it trigger a genuine emotional response quickly?
3. Originality       — Is the angle fresh, or is this a tired cliché?
4. Platform Fit      — Is the structure/tone right for the target platform?
5. Trend Alignment   — Does it tap into current cultural conversations?

Return ONLY a valid JSON object with these exact keys:
{
  "relatability": <float 0-10>,
  "emotional_hook": <float 0-10>,
  "originality": <float 0-10>,
  "platform_fit": <float 0-10>,
  "trend_alignment": <float 0-10>,
  "feedback": "<1–3 specific, actionable sentences for improvement>"
}

Be precise. Decimals are fine (e.g. 7.5). Do not add commentary outside the JSON.
"""


def _build_user_prompt(
    story_fragments: list[dict],
    deep_dive_analysis: dict,
    story_outline: dict | None,
) -> str:
    """Compose the user-facing validation prompt."""
    fragments_text = "\n".join(
        f"- [{f.get('emotion', 'neutral')}] {f.get('text', '')}"
        for f in story_fragments
    )

    outline_text = "No outline yet — evaluating raw fragments."
    if story_outline:
        outline_text = (
            f"Title: {story_outline.get('title', '')}\n"
            f"Hook: {story_outline.get('hook', '')}\n"
            f"Setup: {story_outline.get('setup', '')}\n"
            f"Turning Point: {story_outline.get('turning_point', '')}\n"
            f"Struggle: {story_outline.get('struggle', '')}\n"
            f"Resolution: {story_outline.get('resolution', '')}\n"
            f"Punchline: {story_outline.get('punchline', '')}\n"
            f"Platform: {story_outline.get('platform', 'general')}\n"
            f"Estimated Duration: {story_outline.get('estimated_duration', 'unknown')}"
        )

    themes = deep_dive_analysis.get("themes", []) if deep_dive_analysis else []
    themes_text = ", ".join(themes) if themes else "none identified"

    return (
        f"=== STORY FRAGMENTS ===\n{fragments_text}\n\n"
        f"=== DEEP DIVE THEMES ===\n{themes_text}\n\n"
        f"=== STORY OUTLINE ===\n{outline_text}\n\n"
        "Please score this story concept."
    )


# ─── Node ─────────────────────────────────────────────────────────────────────


def validator_node(state: ArcwrightState) -> dict:
    """
    LangGraph node: validate story quality and return a ValidationResult.

    Reads:
        story_fragments, deep_dive_analysis, story_outline

    Returns:
        validation_result (ValidationResult), debate_rounds + 1, agent_notes
    """
    logger.info("Validator node starting.")

    story_fragments: list[dict] = state.get("story_fragments", [])
    deep_dive_analysis: dict = state.get("deep_dive_analysis", {}) or {}
    story_outline: dict | None = state.get("story_outline")
    debate_rounds: int = state.get("debate_rounds", 0)

    notes: list[AgentNote] = []

    try:
        user_prompt = _build_user_prompt(story_fragments, deep_dive_analysis, story_outline)

        response = _get_llm().invoke(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )

        raw = response.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        scores: dict = json.loads(raw)

        relatability: float = float(scores.get("relatability", 0))
        emotional_hook: float = float(scores.get("emotional_hook", 0))
        originality: float = float(scores.get("originality", 0))
        platform_fit: float = float(scores.get("platform_fit", 0))
        trend_alignment: float = float(scores.get("trend_alignment", 0))
        feedback: str = scores.get("feedback", "No feedback provided.")

        total: float = relatability + emotional_hook + originality + platform_fit + trend_alignment
        passed: bool = total >= 35.0

        validation_result: ValidationResult = {
            "score": round(total, 2),
            "relatability": relatability,
            "emotional_hook": emotional_hook,
            "originality": originality,
            "platform_fit": platform_fit,
            "trend_alignment": trend_alignment,
            "feedback": feedback,
            "passed": passed,
        }

        verdict = "PASSED ✅" if passed else "FAILED ❌"
        notes.append(
            AgentNote(
                agent="validator",
                note_type="insight",
                content=(
                    f"Validation round {debate_rounds + 1}: Score {total:.1f}/50 — {verdict}. "
                    f"Feedback: {feedback}"
                ),
            )
        )

        logger.info("Validation complete. Score=%.1f passed=%s", total, passed)

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse validator LLM response as JSON: %s", exc)
        validation_result = _fallback_result(f"JSON parse error: {exc}")
        notes.append(
            AgentNote(
                agent="validator",
                note_type="flag",
                content=f"JSON parse error in validator: {exc}",
            )
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Validator node error: %s", exc)
        validation_result = _fallback_result(str(exc))
        notes.append(
            AgentNote(
                agent="validator",
                note_type="flag",
                content=f"Validator exception: {exc}",
            )
        )

    return {
        "validation_result": validation_result,
        "debate_rounds": debate_rounds + 1,
        "agent_notes": notes,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _fallback_result(reason: str) -> ValidationResult:
    """Return a zero-score ValidationResult on error so the graph can continue."""
    return ValidationResult(
        score=0.0,
        relatability=0.0,
        emotional_hook=0.0,
        originality=0.0,
        platform_fit=0.0,
        trend_alignment=0.0,
        feedback=f"Validation failed due to error: {reason}",
        passed=False,
    )
