"""
Story Director — supervisor that routes between all agents.
Controls pipeline flow via current_phase state machine.
Also contains user_approval_node for human-in-the-loop.
"""
from typing import Literal
from langgraph.types import interrupt, Command

from config import settings
from agents.state import ArcwrightState


# ── Story Director Routing ─────────────────────────────────────────────────────

def story_director_node(state: ArcwrightState, llm=None) -> dict:
    """
    Story Director node — evaluates state and updates current_phase.
    Pure logic node: no LLM call, just phase transitions.

    Reads:  current_phase, story_fragments, deep_dive_analysis, validation_result, etc.
    Writes: current_phase
    """
    phase = state.get("current_phase", "mining")
    messages = state.get("messages", [])
    fragments = state.get("story_fragments", [])
    deep_dive = state.get("deep_dive_analysis", {})
    validation = state.get("validation_result")
    outline = state.get("story_outline")
    debate_rounds = state.get("debate_rounds", 0)

    if phase == "mining":
        # Extract fragments ready signal from last message if any
        miner_ready = False
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content") and "[FRAGMENTS_READY]" in last_msg.content:
                miner_ready = True
            elif isinstance(last_msg, dict) and "[FRAGMENTS_READY]" in last_msg.get("content", ""):
                miner_ready = True
                
        if len(fragments) >= settings.MIN_STORY_FRAGMENTS or miner_ready:
            return {"current_phase": "enriching"}

    # Enriching → Outlining transition (after BOTH parallel agents complete)
    # Both deep_dive (dict with keys) and web_research (non-empty list) must be ready
    # Note: web_research might be empty if TAVILY_API_KEY is not set, so we only check if deep_dive is done
    if phase == "enriching" and deep_dive and not outline:
        return {"current_phase": "outlining"}

    # Outlining → Validating (after outline is created)
    if phase == "outlining" and outline:
        return {"current_phase": "validating"}

    # Validating — check if debate rounds maxed
    if phase == "validating" and validation:
        if validation.get("passed"):
            return {}  # Stay in validating, routing handles user_approval
        if debate_rounds >= settings.MAX_DEBATE_ROUNDS:
            # Story Director arbitrates — force proceed
            return {"current_phase": "outlining", "debate_rounds": 0}

    return {}


def story_director_routing(state: ArcwrightState) -> str | list:
    """
    Routing function for Story Director conditional edges.
    Returns next node name (or list of Send() for parallel execution).
    """
    from langgraph.types import Send

    phase = state.get("current_phase", "mining")
    messages = state.get("messages", [])
    fragments = state.get("story_fragments", [])
    deep_dive = state.get("deep_dive_analysis", {})
    web_research = state.get("web_research", [])
    outline = state.get("story_outline")
    validation = state.get("validation_result")
    outline_approved = state.get("outline_approved", False)
    debate_rounds = state.get("debate_rounds", 0)

    # ── Mining phase ──────────────────────────────────────────────────────────
    if phase == "mining":
        # Extract fragments ready signal from last message if any
        miner_ready = False
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content") and "[FRAGMENTS_READY]" in last_msg.content:
                miner_ready = True
            elif isinstance(last_msg, dict) and "[FRAGMENTS_READY]" in last_msg.get("content", ""):
                miner_ready = True

        if len(fragments) < settings.MIN_STORY_FRAGMENTS and not miner_ready:
            rag_context = state.get("rag_context", [])
            if not rag_context:
                return "rag_librarian"  # Get RAG context first for smart questions
            return "story_miner"        # Then mine with RAG-guided questions
        # Enough fragments — transition handled by story_director_node

    # ── Enriching phase ───────────────────────────────────────────────────────
    if phase == "enriching":
        missing = []
        # Only dispatch agents that haven't completed yet (avoid re-running done work)
        if not deep_dive:
            missing.append(Send("deep_dive", state))
        if not web_research and settings.TAVILY_API_KEY:
            missing.append(Send("web_researcher", state))
        if missing:
            return missing  # Parallel Send() for whichever is still missing
        # Both done — Director node will transition phase on next tick
        return "story_director"

    # ── Outlining phase ───────────────────────────────────────────────────────
    if phase == "outlining":
        return "outline_writer"

    # Validating phase ──────────────────────────────────────────────────────
    if phase == "validating":
        if outline and not validation:
            return "validator"
        if validation:
            if validation.get("passed"):
                return "user_approval"
            # Debate loop — debate_rounds tracking is in validator_node
            if debate_rounds >= settings.MAX_DEBATE_ROUNDS:
                # Director arbitrates: force proceed to user
                return "user_approval"
            return "story_miner"  # Loop back with validator critique

    # ── Scripting phase ───────────────────────────────────────────────────────
    if phase == "scripting":
        if outline_approved:
            return "script_writer"
        return "user_approval"

    # ── Complete ──────────────────────────────────────────────────────────────
    if phase == "complete":
        from langgraph.graph import END
        return END

    # Default fallback
    return "story_miner"


# ── Validator Debate Routing ───────────────────────────────────────────────────

def validator_debate_routing(state: ArcwrightState) -> str:
    """
    Routing function after validator node.
    Decides: outline_writer (revision), story_miner (debate), or story_director (pass/arbitrate).
    """
    validation = state.get("validation_result", {})
    score = validation.get("score", 0) if validation else 0
    rounds = state.get("debate_rounds", 0)

    if score >= settings.VALIDATOR_PASS_THRESHOLD:
        # PASS → back to Story Director → user_approval
        return "story_director"

    if rounds >= settings.MAX_DEBATE_ROUNDS:
        # Max rounds reached → Story Director arbitrates
        return "story_director"

    if score >= 25:
        # REVISE: loop to outline_writer with feedback
        return "outline_writer"

    # REJECT (<25): need new material from Story Miner
    return "story_miner"


# ── Human-in-the-Loop: User Approval Node ────────────────────────────────────

def user_approval_node(state: ArcwrightState) -> dict:
    """
    User Approval node — interrupts pipeline and waits for user decision.
    Uses LangGraph interrupt() for HITL pattern.

    The caller (CLI/API) resumes with Command(resume="approve"|"revise"|"reject")
    """
    outline = state.get("story_outline", {})

    # Format outline for user display
    outline_display = {
        "title": outline.get("title", ""),
        "hook": outline.get("hook", ""),
        "setup": outline.get("setup", ""),
        "turning_point": outline.get("turning_point", ""),
        "struggle": outline.get("struggle", ""),
        "resolution": outline.get("resolution", ""),
        "punchline": outline.get("punchline", ""),
        "platform": outline.get("platform", ""),
        "duration": outline.get("estimated_duration", ""),
    }

    # Pause and surface outline to user
    # interrupt() saves state — resumable via Command(resume=...)
    decision = interrupt({
        "type": "outline_approval",
        "outline": outline_display,
        "message": "Here's your story outline. What would you like to do?",
        "options": ["approve", "revise", "reject"],
    })

    # Process user decision
    if decision == "approve":
        return {
            "outline_approved": True,
            "current_phase": "scripting",
        }
    elif decision == "revise":
        return {
            "outline_approved": False,
            "current_phase": "outlining",
            "validation_result": None,   # Reset validation for fresh pass
        }
    else:  # reject
        return {
            "outline_approved": False,
            "current_phase": "mining",
            "story_outline": None,
            "validation_result": None,
            "debate_rounds": 0,
        }
