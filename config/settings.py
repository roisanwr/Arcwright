"""
Arcwright configuration — API keys, model names, paths.
Load from environment variables, with fallbacks.
"""

import os
from pathlib import Path

# ── Project paths ──────────────────────────────────────────────────
PROJECT_ROOT    = Path(__file__).resolve().parent
FORGE_DIR       = PROJECT_ROOT / "forge"
CHROMA_DIR      = FORGE_DIR / "output" / "chroma_db"
CHROMA_COLLECTION = "storytelling_books"

# ── LLM config ────────────────────────────────────────────────────
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL       = os.environ.get("ARCWRIGHT_LLM", "gpt-4o-mini")

# ── Embedding ──────────────────────────────────────────────────────
EMBEDDING_MODEL = "BAAI/bge-m3"

# ── Agent config ──────────────────────────────────────────────────
MAX_INTERVIEW_ROUNDS = 5    # Max rounds before forcing to outline
MAX_DEBATE_ROUNDS    = 3    # Max validator↔miner debate rounds
VALIDATION_PASS_SCORE = 35  # Out of 50
MIN_STORY_FRAGMENTS  = 2    # Min fragments before moving to enrich

# ── Validate on import ────────────────────────────────────────────
if not OPENAI_API_KEY:
    import warnings
    warnings.warn(
        "OPENAI_API_KEY not set. Set it with: export OPENAI_API_KEY='sk-...'",
        stacklevel=2
    )
