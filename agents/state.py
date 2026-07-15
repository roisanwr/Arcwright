"""
ArcwrightState — shared state schema for all agents.
All agent communication happens via this TypedDict (Blackboard pattern).
No direct agent-to-agent calls.
"""
import operator
from typing import Annotated, Literal, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


# ── Sub-TypedDicts ────────────────────────────────────────────────────────────

class UserProfile(TypedDict):
    name: str
    platform_target: Literal["youtube", "tiktok", "podcast", "blog", "general"]
    session_count: int
    preferred_language: str


class StoryFragment(TypedDict):
    id: str
    text: str
    emotion: Optional[str]
    timestamp: str


class AgentNote(TypedDict):
    agent_name: str
    note_type: Literal["question", "insight", "flag", "suggestion", "critique"]
    content: str


class ValidationResult(TypedDict):
    score: float                        # 0–50
    criteria_scores: dict[str, float]   # {"relatability": 8, ...}
    feedback: str
    passed: bool


class StoryOutline(TypedDict):
    title: str
    hook: str
    setup: str
    turning_point: str
    struggle: str
    resolution: str
    punchline: str
    platform: str
    estimated_duration: str


class OutputScript(TypedDict):
    title: str
    body: str
    platform_variant: str
    voice_notes: dict[str, str]

class ThoughtProcess(TypedDict):
    agent: str
    timestamp: str
    thought: str
    data: Optional[dict[str, Any]]

# ── Main Session State ────────────────────────────────────────────────────────

class ArcwrightState(TypedDict):
    # ── Session metadata ──────────────────────────────────────────
    session_id: str
    current_phase: Literal[
        "mining", "enriching", "validating", "outlining", "scripting", "complete"
    ]

    # ── User context ──────────────────────────────────────────────
    user_profile: UserProfile
    messages: Annotated[list, add_messages]   # Full chat history

    # ── Story discovery (append-only) ─────────────────────────────
    story_fragments: Annotated[list[StoryFragment], operator.add]
    interview_questions_asked: Annotated[list[str], operator.add]

    # ── Inter-agent communication board (append-only) ─────────────
    agent_notes: Annotated[list[AgentNote], operator.add]
    thought_process: Annotated[list[ThoughtProcess], operator.add] # For Dev Debugging

    # ── Knowledge enrichment (overwrite each cycle) ───────────────
    rag_context: list[dict]          # Latest RAG results
    web_research: list[dict]         # Latest web research
    deep_dive_analysis: dict         # Multi-perspective analysis

    # ── Validation ────────────────────────────────────────────────
    validation_result: Optional[ValidationResult]
    debate_rounds: int
    debate_log: Annotated[list[dict], operator.add]

    # ── Output ────────────────────────────────────────────────────
    story_outline: Optional[StoryOutline]
    output_script: Optional[OutputScript]

    # ── Control flags ─────────────────────────────────────────────
    outline_approved: bool
    error_count: int
