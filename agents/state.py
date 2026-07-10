"""
ArcwrightState — shared state schema for all agents.
Every agent reads from and writes to this TypedDict via LangGraph.
"""

from typing import TypedDict, Annotated, Literal, Optional
from langgraph.graph.message import add_messages


# ─── Sub-types ────────────────────────────────────────────────────

class StoryFragment(TypedDict):
    """A piece of story material extracted from user."""
    text: str
    emotion: Optional[str]
    theme: Optional[str]


class ValidationResult(TypedDict):
    """Validator agent output."""
    score: float                    # 0-50 total
    relatability: float             # 0-10
    emotional_hook: float           # 0-10
    originality: float              # 0-10
    platform_fit: float             # 0-10
    trend_alignment: float          # 0-10
    feedback: str                   # specific improvement notes
    passed: bool                    # >= 35 = pass


class StoryOutline(TypedDict):
    """Outline Writer output."""
    title: str
    hook: str           # Opening line that grabs attention
    setup: str          # Context — who, when, where
    turning_point: str  # The moment things changed
    struggle: str       # The journey/conflict
    resolution: str     # How it ended
    punchline: str      # The takeaway / relatable insight
    platform: str       # youtube | tiktok | podcast | blog
    estimated_duration: str


class OutputScript(TypedDict):
    """Script Writer final output."""
    title: str
    body: str           # Full narrative script
    platform: str
    word_count: int


class AgentNote(TypedDict):
    """Inter-agent communication board entry."""
    agent: str
    note_type: Literal["insight", "flag", "question", "critique"]
    content: str


# ─── Main State ───────────────────────────────────────────────────

class ArcwrightState(TypedDict):
    """
    Shared state for all Arcwright agents.
    LangGraph passes this between every node.
    """

    # ── Session ──────────────────────────────────────────────────
    session_id: str
    current_phase: Literal[
        "mining",       # Story Miner gathering fragments
        "enriching",    # Deep Dive + Web Researcher running
        "validating",   # Validator scoring outline
        "outlining",    # Outline Writer building structure
        "scripting",    # Script Writer producing final output
        "complete",     # Done
    ]

    # ── Conversation ─────────────────────────────────────────────
    messages: Annotated[list, add_messages]     # Full chat history
    platform_target: str                         # youtube|tiktok|podcast|blog|general

    # ── Story Discovery ──────────────────────────────────────────
    story_fragments: Annotated[list[StoryFragment], lambda a, b: a + b]
    interview_round: int                         # How many Q&A rounds done

    # ── Knowledge Enrichment ─────────────────────────────────────
    rag_context: list[dict]                      # RAG Librarian results
    web_research: list[dict]                     # Web Researcher results
    deep_dive_analysis: dict                     # Deep Dive output

    # ── Agent Notes Board ────────────────────────────────────────
    agent_notes: Annotated[list[AgentNote], lambda a, b: a + b]

    # ── Validation ───────────────────────────────────────────────
    validation_result: Optional[ValidationResult]
    debate_rounds: int                           # Validator↔Miner debate count

    # ── Output ───────────────────────────────────────────────────
    story_outline: Optional[StoryOutline]
    outline_approved: bool                       # User approved outline?
    output_script: Optional[OutputScript]

    # ── Controls ─────────────────────────────────────────────────
    error_count: int
    next_agent: Optional[str]                    # Director sets this for routing
