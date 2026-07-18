"""
Story Director — supervisor that routes between all agents.
Controls pipeline flow via current_phase state machine.
Also contains user_approval_node for human-in-the-loop.

Updated routing logic:
- RAG bootstrap sebelum Story Miner pertama kali
- Debate loop tidak di-bypass lagi
- targeted_probe_mode dihandle dengan benar
"""
from typing import Literal
from datetime import datetime
from langgraph.types import interrupt, Command

from config import settings
from agents.state import ArcwrightState, ThoughtProcess


# ── Story Director Node ───────────────────────────────────────────────────────

def story_director_node(state: ArcwrightState, llm=None) -> dict:
    """
    Story Director node — evaluates state and updates current_phase.
    Pure logic node: no LLM call, just phase transitions.

    Reads:  current_phase, story_fragments, deep_dive_analysis, validation_result, etc.
    Writes: current_phase, thought_process
    """
    phase = state.get("current_phase", "mining")
    messages = state.get("messages", [])
    fragments = state.get("story_fragments", [])
    deep_dive = state.get("deep_dive_analysis", {})
    validation = state.get("validation_result")
    outline = state.get("story_outline")
    debate_rounds = state.get("debate_rounds", 0)

    # Count quality fragments
    quality_count = sum(
        1 for f in fragments
        if f.get("quality_score", 0) >= settings.FRAGMENT_QUALITY_THRESHOLD
    )

    thought = ThoughtProcess(
        agent="story_director",
        timestamp=datetime.now().isoformat(),
        thought=f"Phase='{phase}'. Fragments: {len(fragments)} total, {quality_count} quality.",
        data={"phase": phase, "fragment_count": len(fragments), "quality_count": quality_count}
    )

    # ── Mining → Enriching ──────────────────────────────────────────────────
    if phase == "mining":
        miner_ready = _check_fragments_ready(messages)
        sufficient_quality = quality_count >= settings.MIN_STORY_FRAGMENTS

        if sufficient_quality or miner_ready:
            thought["thought"] += f" {quality_count} quality fragments. Transitioning to 'enriching'."
            return {"current_phase": "enriching", "thought_process": [thought]}

    # ── Enriching → Outlining ───────────────────────────────────────────────
    if phase == "enriching" and deep_dive and not outline:
        thought["thought"] += " Enrichment complete. Transitioning to 'outlining'."
        return {"current_phase": "outlining", "thought_process": [thought]}

    # ── Outlining → Validating ──────────────────────────────────────────────
    if phase == "outlining" and outline:
        thought["thought"] += " Outline generated. Transitioning to 'validating'."
        return {"current_phase": "validating", "thought_process": [thought]}

    # ── Validating ──────────────────────────────────────────────────────────
    if phase == "validating" and validation:
        if validation.get("passed"):
            thought["thought"] += " Validation passed. Routing to user approval."
            return {"thought_process": [thought]}

        if debate_rounds >= settings.MAX_DEBATE_ROUNDS:
            thought["thought"] += f" Max debate rounds ({settings.MAX_DEBATE_ROUNDS}) reached. Forcing user approval."
            return {
                "targeted_probe_mode": False,
                "thought_process": [thought],
            }

        thought["thought"] += f" Validation failed (round {debate_rounds}). Routing back for more material."
        return {"thought_process": [thought]}

    thought["thought"] += " No phase transition needed."
    return {"thought_process": [thought]}


def _check_fragments_ready(messages: list) -> bool:
    """Check if Story Miner signaled [FRAGMENTS_READY] in last AI message."""
    for msg in reversed(messages):
        if hasattr(msg, "content") and "[FRAGMENTS_READY]" in msg.content:
            return True
        if isinstance(msg, dict) and "[FRAGMENTS_READY]" in msg.get("content", ""):
            return True
    return False


# ── Story Director Routing ────────────────────────────────────────────────────

def story_director_routing(state: ArcwrightState) -> str | list:
    """
    Routing function for Story Director conditional edges.
    Returns next node name (or list of Send() for parallel execution).
    """
    from langgraph.types import Send
    from langgraph.graph import END

    phase = state.get("current_phase", "mining")
    fragments = state.get("story_fragments", [])
    deep_dive = state.get("deep_dive_analysis", {})
    web_research = state.get("web_research", [])
    outline = state.get("story_outline")
    validation = state.get("validation_result")
    outline_approved = state.get("outline_approved", False)
    debate_rounds = state.get("debate_rounds", 0)
    rag_bootstrapped = state.get("rag_bootstrapped", False)
    rag_fragment_count = state.get("rag_fragment_count", 0)
    targeted_probe = state.get("targeted_probe_mode", False)

    quality_count = sum(
        1 for f in fragments
        if f.get("quality_score", 0) >= settings.FRAGMENT_QUALITY_THRESHOLD
    )

    # ── Mining phase ────────────────────────────────────────────────────────
    if phase == "mining":
        miner_ready = _check_fragments_ready(state.get("messages", []))
        sufficient = quality_count >= settings.MIN_STORY_FRAGMENTS

        if not sufficient and not miner_ready:
            # 1. Bootstrap RAG sebelum interview pertama
            if not rag_bootstrapped:
                return "rag_librarian"

            # 2. Jika ada fragment baru sejak RAG terakhir → query RAG dulu
            if len(fragments) > rag_fragment_count:
                return "rag_librarian"

            # 3. Kalau validator set targeted_probe → Story Miner tanya targeted
            # 4. Normal interview
            return "story_miner"

        # Enough quality fragments → Director node transition to enriching

    # ── Enriching phase ─────────────────────────────────────────────────────
    if phase == "enriching":
        missing = []
        if not deep_dive:
            missing.append(Send("deep_dive", state))
        if not web_research and settings.TAVILY_API_KEY:
            missing.append(Send("web_researcher", state))
        if missing:
            return missing  # Parallel Send()
        return "story_director"  # Both done → Director transitions phase

    # ── Outlining phase ─────────────────────────────────────────────────────
    if phase == "outlining":
        # Query RAG for outlining context if not already done
        rag_results = state.get("rag_results", [])
        has_outlining_rag = any(r.get("query_purpose") == "outlining" for r in rag_results)
        if not has_outlining_rag:
            return "rag_librarian"
        return "outline_writer"

    # ── Validating phase ────────────────────────────────────────────────────
    if phase == "validating":
        if outline and not validation:
            return "validator"

        if validation:
            if validation.get("passed"):
                return "user_approval"

            # Max rounds → force approval (Story Director arbitrates)
            if debate_rounds >= settings.MAX_DEBATE_ROUNDS:
                return "user_approval"

            # Debate loop aktif:
            # Score 25-34 → Outline Writer revisi (tidak butuh info baru dari user)
            # Score <25 → Story Miner tanya user (targeted_probe_mode=True)
            score = validation.get("score", 0)
            if score >= 25:
                # Outline Writer revisi berdasarkan feedback validator
                return "outline_writer"
            else:
                # Story Miner perlu tanya user lebih lanjut (targeted)
                return "story_miner"

    # ── Scripting phase ─────────────────────────────────────────────────────
    if phase == "scripting":
        if outline_approved:
            # Query RAG for scripting context if not already done
            rag_results = state.get("rag_results", [])
            has_scripting_rag = any(r.get("query_purpose") == "scripting" for r in rag_results)
            if not has_scripting_rag:
                return "rag_librarian"
            return "script_writer"
        return "user_approval"

    # ── Complete ─────────────────────────────────────────────────────────────
    if phase == "complete":
        return END

    # Default fallback
    return "story_miner"


# ── Validator Debate Routing ──────────────────────────────────────────────────

def validator_debate_routing(state: ArcwrightState) -> str:
    """
    Routing function after validator node.
    Decides: outline_writer (revision only), story_miner (need user input), or story_director (pass/arbitrate).
    """
    validation = state.get("validation_result", {})
    score = validation.get("score", 0) if validation else 0
    rounds = state.get("debate_rounds", 0)

    if score >= settings.VALIDATOR_PASS_THRESHOLD:
        return "story_director"

    if rounds >= settings.MAX_DEBATE_ROUNDS:
        return "story_director"

    if score >= 25:
        # REVISE: outline structure okay, just needs rewriting → Outline Writer
        return "outline_writer"

    # REJECT (<25): need new story material from user → Story Miner (targeted mode)
    return "story_miner"


# ── Human-in-the-Loop: User Approval Node ────────────────────────────────────

def user_approval_node(state: ArcwrightState) -> dict:
    """
    User Approval node — interrupts pipeline and waits for user decision.
    Uses LangGraph interrupt() for HITL pattern.

    The caller (CLI/API) resumes with Command(resume="approve"|"revise"|"reject")
    """
    outline = state.get("story_outline", {})

    outline_display = {
        "title":         outline.get("title", ""),
        "hook":          outline.get("hook", ""),
        "setup":         outline.get("setup", ""),
        "turning_point": outline.get("turning_point", ""),
        "struggle":      outline.get("struggle", ""),
        "resolution":    outline.get("resolution", ""),
        "punchline":     outline.get("punchline", ""),
        "platform":      outline.get("platform", ""),
        "duration":      outline.get("estimated_duration", ""),
    }

    # Pause and surface outline to user
    decision = interrupt({
        "type":    "outline_approval",
        "outline": outline_display,
        "message": "Here's your story outline. What would you like to do?",
        "options": ["approve", "revise", "reject"],
    })

    if decision == "approve":
        return {
            "outline_approved": True,
            "current_phase":    "scripting",
        }
    elif decision == "revise":
        return {
            "outline_approved":  False,
            "current_phase":     "outlining",
            "validation_result": None,
            "story_outline":     None,
        }
    else:  # reject
        return {
            "outline_approved":  False,
            "current_phase":     "mining",
            "story_outline":     None,
            "validation_result": None,
            "debate_rounds":     0,
            "targeted_probe_mode": False,
            # Pertahankan fragments — user mungkin mau explore cerita berbeda dari material yang sama
        }
