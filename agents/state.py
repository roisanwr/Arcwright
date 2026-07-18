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
    quality_score: int          # 0-10: kualitas fragment (sensory detail, emotion, specificity)
    source_turn: int            # turn ke berapa fragment ini diambil


class AgentNote(TypedDict):
    agent_name: str
    note_type: Literal["question", "insight", "flag", "suggestion", "critique", "targeted_probe"]
    content: str


class ValidationResult(TypedDict):
    score: float                        # 0–50
    criteria_scores: dict[str, float]   # {"relatability": 8, ...}
    feedback: str
    passed: bool
    weak_areas: list[str]               # ["emotional_hook", "originality"] — area yang perlu digali
    targeted_question: str              # Pertanyaan spesifik yang harus Story Miner tanyakan ke user


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


class RAGChunk(TypedDict):
    text: str                   # Full chunk text — tidak di-truncate
    source: str                 # "Book Title — Section Name"
    relevance_score: float      # MMR score dari retrieval


class RAGResult(TypedDict):
    query: str                  # Query yang digunakan
    chunks: list[RAGChunk]      # Raw chunks dari Qdrant (5 chunks)
    synthesis: str              # LLM synthesis — rangkuman actionable dari chunks
    source_books: list[str]     # Daftar buku yang dikutip
    query_purpose: str          # "mining_bootstrap" | "mining_probe" | "enriching" | "outlining" | "scripting"


# ── Main Session State ────────────────────────────────────────────────────────

class ArcwrightState(TypedDict):
    # ── Session metadata ──────────────────────────────────────────
    session_id: str
    current_phase: Literal[
        "mining", "enriching", "validating", "outlining", "scripting", "complete"
    ]
    turn_count: int             # Hitungan turn interview (untuk tracking)

    # ── User context ──────────────────────────────────────────────
    user_profile: UserProfile
    messages: Annotated[list, add_messages]   # Full chat history

    # ── Story discovery (append-only) ─────────────────────────────
    story_fragments: Annotated[list[StoryFragment], operator.add]
    interview_questions_asked: Annotated[list[str], operator.add]

    # ── Inter-agent communication board (append-only) ─────────────
    agent_notes: Annotated[list[AgentNote], operator.add]
    thought_process: Annotated[list[ThoughtProcess], operator.add]  # Dev debugging

    # ── Knowledge enrichment ──────────────────────────────────────
    # Structured RAG results — tidak di-truncate, per-purpose
    rag_results: Annotated[list[RAGResult], operator.add]   # Semua RAG queries (append)
    rag_context: list[dict]          # Legacy compat — diisi dari rag_results terbaru
    web_research: list[dict]         # Latest web research
    deep_dive_analysis: dict         # Multi-perspective analysis

    # ── Validation ────────────────────────────────────────────────
    validation_result: Optional[ValidationResult]
    debate_rounds: int
    debate_log: Annotated[list[dict], operator.add]

    # ── Output ────────────────────────────────────────────────────
    story_outline: Optional[StoryOutline]
    output_script: Optional[OutputScript]

    # ── Continuous RAG tracking ──────────────────────────────────
    rag_fragment_count: int         # Berapa fragments udah diproses Librarian
    rag_bootstrapped: bool          # Apakah RAG sudah di-bootstrap sebelum interview pertama

    # ── Control flags ─────────────────────────────────────────────
    outline_approved: bool
    error_count: int
    targeted_probe_mode: bool       # True kalau Story Miner lagi follow-up dari Validator critique
