"""
script_writer.py — Final Narrative Script Writer Agent

Converts an approved StoryOutline into a full, platform-native narrative script.
Uses a self-refine loop: generate → internal critique → improve.
Only runs after outline_approved == True.
Runs as a LangGraph node.
"""

from __future__ import annotations

import logging
import os

from langchain_openai import ChatOpenAI

from agents.state import AgentNote, ArcwrightState, OutputScript

logger = logging.getLogger(__name__)

# ─── LLM ──────────────────────────────────────────────────────────────────────

def _get_llm() -> ChatOpenAI:
    """Lazy LLM init — avoids crash on import when API key not set."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.8,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

def _get_critic_llm() -> ChatOpenAI:
    """Lazy critic LLM init."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

# ─── Prompts ──────────────────────────────────────────────────────────────────

_WRITER_SYSTEM = """\
You are a gifted personal-narrative writer who specialises in short-form
storytelling for digital platforms. Your scripts feel real — like something
a person is actually saying, not performing.

Voice rules:
- First-person ("I", "we"), past tense unless reflecting in present
- Conversational cadence: short sentences, natural pauses, occasional fragments
- Specific sensory details over vague emotion-words ("my hands went cold" not "I was scared")
- Mirror the speaker's vocabulary and energy extracted from their original fragments
- No corporate buzzwords, no generic life-lesson signposting

Platform formatting:
- youtube:  Full spoken script with natural paragraph breaks. Include [PAUSE] markers.
- tiktok:   Ultra-tight, punchy lines. One idea per line. 150–250 words max.
- podcast:  Flowing narrative paragraphs, richer descriptions, ~500–800 words.
- blog:     Prose with subheadings (##), punchy opener, insight-led closer.
- general:  Clean spoken-word format, 300–500 words.

Return ONLY the finished script text — no title header, no notes, no formatting labels.
"""

_CRITIC_SYSTEM = """\
You are a ruthless script editor. Read the script below and identify the
3 most important improvements needed. Be specific and brief.

Focus on:
1. Authenticity — does it sound like a real person or a robot?
2. Pacing — are there dead spots or rushed moments?
3. Emotional impact — does the punchline actually land?

Reply in this exact format (no other text):
CRITIQUE 1: <issue and suggested fix>
CRITIQUE 2: <issue and suggested fix>
CRITIQUE 3: <issue and suggested fix>
"""

_REFINE_SYSTEM = """\
You are the same gifted personal-narrative writer. You've received editorial
critiques on your first draft. Rewrite the script incorporating these fixes.
Keep everything that already works. Return ONLY the improved script text.
"""


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _extract_voice_cues(messages: list) -> str:
    """Pull vocabulary and energy cues from early user messages."""
    user_texts: list[str] = []
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "human":
            user_texts.append(msg.content)
        elif isinstance(msg, dict) and msg.get("role") == "user":
            user_texts.append(msg.get("content", ""))
        if len(user_texts) >= 6:  # first 6 user turns is enough
            break

    if not user_texts:
        return "No voice samples available — use a warm, conversational tone."

    sample = " | ".join(t[:200] for t in user_texts)
    return f"Voice sample from the speaker: {sample}"


def _build_writer_prompt(
    outline: dict,
    story_fragments: list[dict],
    voice_cues: str,
    platform: str,
) -> str:
    """Compose the first-draft writing prompt."""
    fragments_text = "\n".join(
        f"- [{f.get('emotion', 'neutral')}] {f.get('text', '')}"
        for f in story_fragments
    )

    return (
        f"TARGET PLATFORM: {platform}\n\n"
        f"=== STORY OUTLINE ===\n"
        f"Title: {outline.get('title', '')}\n"
        f"Hook: {outline.get('hook', '')}\n"
        f"Setup: {outline.get('setup', '')}\n"
        f"Turning Point: {outline.get('turning_point', '')}\n"
        f"Struggle: {outline.get('struggle', '')}\n"
        f"Resolution: {outline.get('resolution', '')}\n"
        f"Punchline: {outline.get('punchline', '')}\n"
        f"Estimated Duration: {outline.get('estimated_duration', 'unknown')}\n\n"
        f"=== ORIGINAL STORY FRAGMENTS ===\n{fragments_text}\n\n"
        f"=== VOICE CALIBRATION ===\n{voice_cues}\n\n"
        "Write the full narrative script now. Make it feel real."
    )


def _build_refine_prompt(draft: str, critique: str, platform: str) -> str:
    """Compose the rewrite prompt with critique incorporated."""
    return (
        f"TARGET PLATFORM: {platform}\n\n"
        f"=== FIRST DRAFT ===\n{draft}\n\n"
        f"=== EDITORIAL CRITIQUES ===\n{critique}\n\n"
        "Rewrite the script incorporating these improvements. "
        "Keep what's already strong."
    )


# ─── Node ─────────────────────────────────────────────────────────────────────


def script_writer_node(state: ArcwrightState) -> dict:
    """
    LangGraph node: produce the final narrative script.

    Only executes after outline_approved == True.
    Uses a self-refine loop: draft → critique → improved draft.

    Reads:
        story_outline, story_fragments, messages, platform_target,
        outline_approved

    Returns:
        output_script (OutputScript), current_phase='complete', agent_notes
    """
    logger.info("Script Writer node starting.")

    outline_approved: bool = state.get("outline_approved", False)
    story_outline: dict | None = state.get("story_outline")
    story_fragments: list[dict] = state.get("story_fragments", [])
    messages: list = state.get("messages", [])
    platform: str = state.get("platform_target", "general")

    notes: list[AgentNote] = []

    # Guard: must have approval
    if not outline_approved:
        logger.warning("Script Writer called without outline approval — skipping.")
        notes.append(
            AgentNote(
                agent="script_writer",
                note_type="flag",
                content="Script Writer skipped: outline not yet approved by user.",
            )
        )
        return {
            "output_script": None,
            "current_phase": "scripting",
            "agent_notes": notes,
        }

    if not story_outline:
        logger.error("Script Writer called with no story_outline.")
        notes.append(
            AgentNote(
                agent="script_writer",
                note_type="flag",
                content="Script Writer error: no story_outline found in state.",
            )
        )
        return {
            "output_script": _fallback_script(platform),
            "current_phase": "complete",
            "agent_notes": notes,
        }

    try:
        voice_cues = _extract_voice_cues(messages)

        # ── Step 1: First draft ───────────────────────────────────────────────
        writer_prompt = _build_writer_prompt(
            story_outline, story_fragments, voice_cues, platform
        )

        draft_response = _get_llm().invoke(
            [
                {"role": "system", "content": _WRITER_SYSTEM},
                {"role": "user", "content": writer_prompt},
            ]
        )
        draft: str = draft_response.content.strip()

        notes.append(
            AgentNote(
                agent="script_writer",
                note_type="insight",
                content=f"First draft generated: {len(draft.split())} words.",
            )
        )

        # ── Step 2: Internal critique ─────────────────────────────────────────
        critique_response = _get_critic_llm().invoke(
            [
                {"role": "system", "content": _CRITIC_SYSTEM},
                {"role": "user", "content": f"=== SCRIPT ===\n{draft}"},
            ]
        )
        critique: str = critique_response.content.strip()

        notes.append(
            AgentNote(
                agent="script_writer",
                note_type="critique",
                content=f"Self-critique: {critique[:300]}",
            )
        )

        # ── Step 3: Refined final draft ───────────────────────────────────────
        refine_prompt = _build_refine_prompt(draft, critique, platform)

        refined_response = _get_llm().invoke(
            [
                {"role": "system", "content": _REFINE_SYSTEM},
                {"role": "user", "content": refine_prompt},
            ]
        )
        final_script: str = refined_response.content.strip()

        word_count: int = len(final_script.split())

        output_script: OutputScript = {
            "title": story_outline.get("title", "Untitled Story"),
            "body": final_script,
            "platform": platform,
            "word_count": word_count,
        }

        notes.append(
            AgentNote(
                agent="script_writer",
                note_type="insight",
                content=(
                    f"Final script '{output_script['title']}' complete: "
                    f"{word_count} words for {platform}."
                ),
            )
        )

        logger.info(
            "Script complete: '%s' — %d words for %s.",
            output_script["title"],
            word_count,
            platform,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("Script Writer node error: %s", exc)
        output_script = _fallback_script(platform)
        notes.append(
            AgentNote(
                agent="script_writer",
                note_type="flag",
                content=f"Script Writer exception: {exc}",
            )
        )

    return {
        "output_script": output_script,
        "current_phase": "complete",
        "agent_notes": notes,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _fallback_script(platform: str) -> OutputScript:
    """Return a placeholder OutputScript on error so the graph can finish."""
    body = (
        "[Script generation failed. Please review agent notes and retry. "
        "Your story outline is still available for manual scripting.]"
    )
    return OutputScript(
        title="Script (generation failed)",
        body=body,
        platform=platform,
        word_count=len(body.split()),
    )
