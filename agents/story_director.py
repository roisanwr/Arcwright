"""
story_director.py — Supervisor Orchestrator for Arcwright

Contains:
  story_director_routing() — decides which node runs next based on state.
  user_approval_node()     — pauses graph for human outline approval via interrupt().
"""

from __future__ import annotations

import logging

from langgraph.graph import END
from langgraph.types import interrupt

from agents.state import AgentNote, ArcwrightState

logger = logging.getLogger(__name__)


# ─── Routing ──────────────────────────────────────────────────────────────────


def story_director_routing(state: ArcwrightState) -> str:
    """
    Supervisor routing function for the Arcwright LangGraph.

    Reads the current state and returns the name of the next node to execute.
    This function is used as a conditional edge source — it must return a string
    that matches a registered node name (or END).

    Args:
        state: The current ArcwrightState shared across all agents.

    Returns:
        Name of the next node to execute, or END sentinel.
    """
    current_phase: str = state.get("current_phase", "mining")
    story_fragments: list = state.get("story_fragments", [])
    rag_context: list = state.get("rag_context") or []
    deep_dive_analysis: dict = state.get("deep_dive_analysis") or {}
    web_research: list = state.get("web_research") or []
    validation_result: dict | None = state.get("validation_result")
    debate_rounds: int = state.get("debate_rounds", 0)

    logger.debug(
        "Director routing: phase=%s fragments=%d rag=%s deep_dive=%s web=%s "
        "validation=%s debate_rounds=%d",
        current_phase,
        len(story_fragments),
        bool(rag_context),
        bool(deep_dive_analysis),
        bool(web_research),
        validation_result is not None,
        debate_rounds,
    )

    # ── Mining phase ──────────────────────────────────────────────────────────
    if current_phase == "mining":
        if len(story_fragments) < 2:
            logger.info("Director → story_miner (need more fragments)")
            return "story_miner"

        if not rag_context:
            logger.info("Director → rag_librarian (no RAG context yet)")
            return "rag_librarian"

        # Enough fragments + RAG context → move to enrichment
        logger.info("Director → deep_dive (transitioning to enriching)")
        return "deep_dive"

    # ── Enriching phase ───────────────────────────────────────────────────────
    if current_phase == "enriching":
        if not deep_dive_analysis:
            logger.info("Director → deep_dive (awaiting deep dive analysis)")
            return "deep_dive"

        if not web_research:
            logger.info("Director → web_researcher (awaiting web research)")
            return "web_researcher"

        # All enrichment complete → build outline
        logger.info("Director → outline_writer (all enrichment done)")
        return "outline_writer"

    # ── Validating phase ──────────────────────────────────────────────────────
    if current_phase == "validating":
        if validation_result and validation_result.get("passed"):
            logger.info("Director → user_approval (validation passed)")
            return "user_approval"

        if debate_rounds >= 3:
            # Force through after 3 rounds regardless of score
            logger.info("Director → user_approval (debate_rounds limit reached)")
            return "user_approval"

        logger.info("Director → story_miner (revise — validation failed, round %d)", debate_rounds)
        return "story_miner"

    # ── Outlining phase ───────────────────────────────────────────────────────
    if current_phase == "outlining":
        logger.info("Director → outline_writer")
        return "outline_writer"

    # ── Scripting phase ───────────────────────────────────────────────────────
    if current_phase == "scripting":
        logger.info("Director → script_writer")
        return "script_writer"

    # ── Complete ──────────────────────────────────────────────────────────────
    if current_phase == "complete":
        logger.info("Director → END")
        return END

    # ── Default / unknown ─────────────────────────────────────────────────────
    logger.warning("Director: unknown phase '%s' — falling back to story_miner", current_phase)
    return "story_miner"


# ─── User Approval Node ───────────────────────────────────────────────────────


def user_approval_node(state: ArcwrightState) -> dict:
    """
    LangGraph node: pause execution and ask the user to approve the story outline.

    Uses LangGraph's interrupt() to yield control back to the caller. When the
    graph is resumed (via graph.update_state() + graph.stream(None, ...)), this
    node continues and marks the outline as approved.

    Reads:
        story_outline — displayed to the user for review.

    Returns:
        outline_approved=True, current_phase='scripting', agent_notes
    """
    logger.info("User Approval node: pausing for human review.")

    story_outline: dict | None = state.get("story_outline")
    notes: list[AgentNote] = []

    # Build a human-readable outline summary to surface via the interrupt
    if story_outline:
        outline_display = (
            f"📖 STORY OUTLINE FOR YOUR APPROVAL\n"
            f"{'─' * 50}\n"
            f"Title:            {story_outline.get('title', 'N/A')}\n"
            f"Platform:         {story_outline.get('platform', 'N/A')}\n"
            f"Est. Duration:    {story_outline.get('estimated_duration', 'N/A')}\n\n"
            f"Hook:             {story_outline.get('hook', '')}\n\n"
            f"Setup:            {story_outline.get('setup', '')}\n\n"
            f"Turning Point:    {story_outline.get('turning_point', '')}\n\n"
            f"Struggle:         {story_outline.get('struggle', '')}\n\n"
            f"Resolution:       {story_outline.get('resolution', '')}\n\n"
            f"Punchline:        {story_outline.get('punchline', '')}\n"
            f"{'─' * 50}\n"
            f"Do you approve this outline? (yes / no + feedback)"
        )
    else:
        outline_display = (
            "⚠️  No outline is available yet. "
            "Type 'yes' to proceed anyway or 'no' to restart."
        )

    try:
        # Pause the graph here — the host app must resume with the user's answer
        user_response: str = interrupt(outline_display)

        approved = str(user_response).strip().lower().startswith("y")

        if approved:
            logger.info("User approved the outline.")
            notes.append(
                AgentNote(
                    agent="story_director",
                    note_type="insight",
                    content="User approved the story outline. Moving to scripting.",
                )
            )
            return {
                "outline_approved": True,
                "current_phase": "scripting",
                "agent_notes": notes,
            }
        else:
            # User rejected — log their feedback and route back for revision
            logger.info("User rejected the outline. Feedback: %s", user_response)
            notes.append(
                AgentNote(
                    agent="story_director",
                    note_type="question",
                    content=f"User rejected outline. Feedback: {user_response}",
                )
            )
            return {
                "outline_approved": False,
                "current_phase": "mining",
                "agent_notes": notes,
            }

    except Exception as exc:  # noqa: BLE001
        # If interrupt is not supported in the current runtime, auto-approve
        logger.warning(
            "interrupt() not available or raised unexpectedly (%s) — auto-approving.", exc
        )
        notes.append(
            AgentNote(
                agent="story_director",
                note_type="flag",
                content=f"User approval interrupt failed ({exc}). Auto-approved outline.",
            )
        )
        return {
            "outline_approved": True,
            "current_phase": "scripting",
            "agent_notes": notes,
        }
