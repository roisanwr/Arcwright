"""
outline_writer.py — Story Outline Builder Agent

Synthesises story fragments, RAG context, deep-dive analysis, and web research
into a structured StoryOutline ready for user approval.
Runs as a LangGraph node.
"""

from __future__ import annotations

import json
import logging
import os


from agents.state import AgentNote, ArcwrightState, StoryOutline

logger = logging.getLogger(__name__)

# ─── LLM ──────────────────────────────────────────────────────────────────────

def _get_llm():
    """Lazy LLM init via factory — supports any provider."""
    from config.settings import get_llm_for_agent
    return get_llm_for_agent("outline_writer")

# ─── Prompt ───────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert story architect who turns raw personal experiences into
compelling, platform-native story outlines.

Given story fragments, contextual knowledge, research, and a target platform,
produce a tight narrative outline that follows this arc:
  Hook → Setup → Turning Point → Struggle → Resolution → Punchline

Platform guidelines:
- youtube:  3–8 minutes, conversational but structured, strong hook in first 30s
- tiktok:   30–90 seconds, ultra-punchy hook, single emotion, no preamble
- podcast:  5–20 minutes, richer detail, dialogue-friendly, atmospheric
- blog:     500–1500 words, reflective tone, SEO-aware title, insight-led ending
- general:  balanced, medium length, universal tone

Return ONLY valid JSON with exactly these keys:
{
  "title": "<compelling, platform-appropriate title>",
  "hook": "<opening line or question that grabs attention immediately>",
  "setup": "<context: who, when, where — just enough>",
  "turning_point": "<the moment everything changed>",
  "struggle": "<the tension, conflict, or journey>",
  "resolution": "<how it resolved or what changed>",
  "punchline": "<the relatable insight or takeaway>",
  "platform": "<youtube|tiktok|podcast|blog|general>",
  "estimated_duration": "<e.g. '4 minutes' or '750 words'>"
}

No commentary outside the JSON. Be vivid, specific, and emotionally honest.
"""


def _build_user_prompt(
    story_fragments: list[dict],
    rag_context: list[dict],
    deep_dive_analysis: dict,
    web_research: list[dict],
    platform: str,
) -> str:
    """Compose the outline-writer prompt from all available material."""
    fragments_text = "\n".join(
        f"- [{f.get('emotion', 'neutral')} / {f.get('theme', 'general')}] {f.get('text', '')}"
        for f in story_fragments
    )

    rag_text = "None available."
    if rag_context:
        rag_snippets = [
            r.get("content", r.get("text", str(r)))[:300]
            for r in rag_context[:5]
        ]
        rag_text = "\n".join(f"• {s}" for s in rag_snippets)

    analysis_text = "None available."
    if deep_dive_analysis:
        themes = deep_dive_analysis.get("themes", [])
        insights = deep_dive_analysis.get("insights", [])
        analysis_text = (
            f"Themes: {', '.join(themes)}\n"
            f"Insights: {' | '.join(insights)}"
        )

    web_text = "None available."
    if web_research:
        web_snippets = [
            r.get("summary", r.get("content", str(r)))[:300]
            for r in web_research[:3]
        ]
        web_text = "\n".join(f"• {s}" for s in web_snippets)

    return (
        f"TARGET PLATFORM: {platform}\n\n"
        f"=== STORY FRAGMENTS ===\n{fragments_text}\n\n"
        f"=== RAG KNOWLEDGE BASE CONTEXT ===\n{rag_text}\n\n"
        f"=== DEEP DIVE ANALYSIS ===\n{analysis_text}\n\n"
        f"=== WEB RESEARCH ===\n{web_text}\n\n"
        "Build the best possible story outline from this material."
    )


# ─── Node ─────────────────────────────────────────────────────────────────────


def outline_writer_node(state: ArcwrightState) -> dict:
    """
    LangGraph node: build a structured StoryOutline from all gathered material.

    Reads:
        story_fragments, rag_context, deep_dive_analysis, web_research,
        platform_target

    Returns:
        story_outline (StoryOutline), current_phase='validating', agent_notes
    """
    logger.info("Outline Writer node starting.")

    story_fragments: list[dict] = state.get("story_fragments", [])
    rag_context: list[dict] = state.get("rag_context", []) or []
    deep_dive_analysis: dict = state.get("deep_dive_analysis", {}) or {}
    web_research: list[dict] = state.get("web_research", []) or []
    platform: str = state.get("platform_target", "general")

    notes: list[AgentNote] = []

    try:
        user_prompt = _build_user_prompt(
            story_fragments, rag_context, deep_dive_analysis, web_research, platform
        )

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

        data: dict = json.loads(raw)

        story_outline: StoryOutline = {
            "title": data.get("title", "Untitled Story"),
            "hook": data.get("hook", ""),
            "setup": data.get("setup", ""),
            "turning_point": data.get("turning_point", ""),
            "struggle": data.get("struggle", ""),
            "resolution": data.get("resolution", ""),
            "punchline": data.get("punchline", ""),
            "platform": data.get("platform", platform),
            "estimated_duration": data.get("estimated_duration", "unknown"),
        }

        notes.append(
            AgentNote(
                agent="outline_writer",
                note_type="insight",
                content=(
                    f"Outline created: '{story_outline['title']}' "
                    f"for {story_outline['platform']} "
                    f"({story_outline['estimated_duration']}). "
                    f"Hook: {story_outline['hook'][:80]}…"
                ),
            )
        )

        logger.info("Outline created: %s", story_outline["title"])

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse outline LLM response as JSON: %s", exc)
        story_outline = _fallback_outline(platform, f"JSON parse error: {exc}")
        notes.append(
            AgentNote(
                agent="outline_writer",
                note_type="flag",
                content=f"JSON parse error in outline_writer: {exc}",
            )
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Outline Writer node error: %s", exc)
        story_outline = _fallback_outline(platform, str(exc))
        notes.append(
            AgentNote(
                agent="outline_writer",
                note_type="flag",
                content=f"Outline Writer exception: {exc}",
            )
        )

    return {
        "story_outline": story_outline,
        "current_phase": "validating",
        "agent_notes": notes,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _fallback_outline(platform: str, reason: str) -> StoryOutline:
    """Return a skeleton StoryOutline on error so the graph can continue."""
    return StoryOutline(
        title="Story Outline (draft)",
        hook="[Hook to be developed]",
        setup="[Setup to be developed]",
        turning_point="[Turning point to be developed]",
        struggle="[Struggle to be developed]",
        resolution="[Resolution to be developed]",
        punchline="[Punchline to be developed]",
        platform=platform,
        estimated_duration="unknown",
    )
