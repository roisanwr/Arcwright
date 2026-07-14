"""
Arcwright LangGraph Pipeline — StateGraph definition and compilation.
Wires all 8 agents together with the Story Director as orchestrator.
Tiap agent lazy-load LLM-nya sendiri via get_llm_for_agent().
"""
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from config.settings import get_llm_for_agent
from agents.state import ArcwrightState
from agents.story_director import story_director_node, user_approval_node
from agents.rag_librarian import rag_librarian_node
from agents.story_miner import story_miner_node
from agents.web_researcher import web_researcher_node
from agents.deep_dive import deep_dive_node
from agents.validator import validator_node
from agents.outline_writer import outline_writer_node
from agents.script_writer import script_writer_node
from graph.edges import story_director_routing, validator_debate_routing


def create_arcwright_graph(checkpointer=None):
    """
    Build and compile the full Arcwright multi-agent graph.
    Tiap agent lazy-load LLM-nya sendiri saat pertama kali dipanggil.

    Args:
        checkpointer: LangGraph checkpointer (default: InMemorySaver for dev).

    Returns:
        Compiled LangGraph StateGraph.
    """
    def make_node(fn, agent_name: str):
        """Wrap agent node — lazy-load per-agent LLM on first call."""
        _llm_ref = [None]  # mutable container for lazy init

        def node(state: ArcwrightState) -> dict:
            if _llm_ref[0] is None:
                _llm_ref[0] = get_llm_for_agent(agent_name)
            return fn(state, _llm_ref[0])

        node.__name__ = fn.__name__
        return node

    builder = StateGraph(ArcwrightState)

    # ── Register nodes — setiap agent pakai LLM config-nya sendiri ───────────
    builder.add_node("story_director", make_node(story_director_node, "story_director"))
    builder.add_node("story_miner",    make_node(story_miner_node,    "story_miner"))
    builder.add_node("rag_librarian",  make_node(rag_librarian_node,  "rag_librarian"))
    builder.add_node("web_researcher", make_node(web_researcher_node, "web_researcher"))
    builder.add_node("deep_dive",      make_node(deep_dive_node,      "deep_dive"))
    builder.add_node("validator",      make_node(validator_node,      "validator"))
    builder.add_node("outline_writer", make_node(outline_writer_node, "outline_writer"))
    builder.add_node("script_writer",  make_node(script_writer_node,  "script_writer"))
    # user_approval_node has no llm — direct registration
    builder.add_node("user_approval",  user_approval_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    builder.add_edge(START, "story_director")

    # ── All agents report back to Story Director ──────────────────────────────
    for agent in ["story_miner", "rag_librarian", "web_researcher",
                  "deep_dive", "outline_writer", "user_approval"]:
        builder.add_edge(agent, "story_director")

    # ── Script Writer → END (final output, no routing needed) ────────────────
    builder.add_edge("script_writer", END)

    # ── Story Director conditional routing ────────────────────────────────────
    builder.add_conditional_edges(
        "story_director",
        story_director_routing,
        {
            "story_director":  "story_director",   # enriching wait-loop self-route
            "story_miner":    "story_miner",
            "rag_librarian":  "rag_librarian",
            "web_researcher": "web_researcher",
            "deep_dive":      "deep_dive",
            "validator":      "validator",
            "outline_writer": "outline_writer",
            "user_approval":  "user_approval",
            "script_writer":  "script_writer",
            END:              END,
        },
    )

    # ── Validator debate routing ───────────────────────────────────────────────
    builder.add_conditional_edges(
        "validator",
        validator_debate_routing,
        {
            "story_director": "story_director",
            "outline_writer": "outline_writer",
            "story_miner":    "story_miner",
        },
    )

    # ── Compile with checkpointer + HITL interrupt ────────────────────────────
    if checkpointer is None:
        checkpointer = InMemorySaver()

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["user_approval"],  # Hanya interrupt sebelum outline approval
    )


def make_initial_state(
    user_name: str = "User",
    platform: str = "general",
    session_id: str = None,
) -> ArcwrightState:
    """Create a fresh ArcwrightState for a new session."""
    return ArcwrightState(
        session_id=session_id or str(uuid.uuid4()),
        current_phase="mining",
        user_profile={
            "name": user_name,
            "platform_target": platform,
            "session_count": 1,
            "preferred_language": "id",
        },
        messages=[],
        story_fragments=[],
        interview_questions_asked=[],
        agent_notes=[],
        rag_context=[],
        web_research=[],
        deep_dive_analysis={},
        validation_result=None,
        debate_rounds=0,
        debate_log=[],
        story_outline=None,
        output_script=None,
        outline_approved=False,
        error_count=0,
    )
