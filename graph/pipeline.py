"""
Arcwright LangGraph Pipeline — StateGraph definition.
Wires all agents into a directed graph with conditional routing.
"""

import uuid
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from agents.state import ArcwrightState


def create_arcwright_graph():
    """
    Build and compile the full Arcwright multi-agent pipeline.

    Flow:
      START → story_director → [story_miner | rag_librarian | deep_dive |
                                 web_researcher | outline_writer | validator |
                                 user_approval | script_writer] → END

    Returns:
        Compiled LangGraph StateGraph with MemorySaver checkpointer.
    """
    # Import agents (late import to avoid circular deps)
    from agents.rag_librarian import rag_librarian_node
    from agents.story_miner import story_miner_node
    from agents.deep_dive import deep_dive_node
    from agents.web_researcher import web_researcher_node
    from agents.validator import validator_node
    from agents.outline_writer import outline_writer_node
    from agents.script_writer import script_writer_node
    from agents.story_director import story_director_routing, user_approval_node

    builder = StateGraph(ArcwrightState)

    # ── Register all nodes ─────────────────────────────────────────
    builder.add_node("story_miner",     story_miner_node)
    builder.add_node("rag_librarian",   rag_librarian_node)
    builder.add_node("deep_dive",       deep_dive_node)
    builder.add_node("web_researcher",  web_researcher_node)
    builder.add_node("validator",       validator_node)
    builder.add_node("outline_writer",  outline_writer_node)
    builder.add_node("script_writer",   script_writer_node)
    builder.add_node("user_approval",   user_approval_node)

    # ── Edges: every agent reports back to director ────────────────
    # Director decides routing via conditional edges
    builder.add_edge(START, "story_miner")   # Always start with Story Miner

    # All agents return to director after their work
    for agent in ["story_miner", "rag_librarian", "deep_dive",
                  "web_researcher", "outline_writer", "validator",
                  "user_approval"]:
        builder.add_conditional_edges(
            agent,
            story_director_routing,
            {
                "story_miner":    "story_miner",
                "rag_librarian":  "rag_librarian",
                "deep_dive":      "deep_dive",
                "web_researcher": "web_researcher",
                "outline_writer": "outline_writer",
                "validator":      "validator",
                "user_approval":  "user_approval",
                "script_writer":  "script_writer",
                END:              END,
            }
        )

    # Script writer always goes to END
    builder.add_edge("script_writer", END)

    # ── Compile with memory checkpointer ──────────────────────────
    checkpointer = MemorySaver()
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["user_approval"],   # Pause for user to approve outline
    )

    return graph


def get_initial_state(platform: str = "general") -> ArcwrightState:
    """Build the initial state for a new session."""
    return {
        "session_id": str(uuid.uuid4())[:8],
        "current_phase": "mining",
        "messages": [],
        "platform_target": platform,
        "story_fragments": [],
        "interview_round": 0,
        "rag_context": [],
        "web_research": [],
        "deep_dive_analysis": {},
        "agent_notes": [],
        "validation_result": None,
        "debate_rounds": 0,
        "story_outline": None,
        "outline_approved": False,
        "output_script": None,
        "error_count": 0,
        "next_agent": None,
    }
