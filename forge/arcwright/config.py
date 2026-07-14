"""Configuration for Arcwright pipeline."""
import os
from pathlib import Path

# Project root (2 levels up from this file = arcwright/ → Arcwright/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ─── Directories ───────────────────────────────────────────
# Note: all data lives under forge/ subdirectory
DATA_DIR = PROJECT_ROOT / "forge" / "data"
BOOKS_DIR = DATA_DIR / "books"
OUTPUT_DIR = PROJECT_ROOT / "forge" / "output"

# Ensure output dirs exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Temporary upload directory
UPLOAD_DIR = PROJECT_ROOT / "forge" / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ─── Models (all free, open source) ────────────────────────
EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL  = "BAAI/bge-reranker-v2-m3"

# ─── Chunking:  Strategy ──────────────────────────────────
# Heading levels to treat as chunk boundaries (1=H1, 2=H2, 3=H3, 4=H4)
# Default: H1/H2/H3 only (H4 requires explicit opt-in)
CHUNK_HEADING_LEVELS = [1, 2, 3]

# Chunk size thresholds (characters)
CHUNK_MIN_CHARS = 150        # Below this → merge with neighbor
CHUNK_MAX_CHARS = 1500       # Above this → flag for semantic refiner
CHUNK_HARD_MAX_CHARS = 2000  # Absolute max — force-split at this

# Chunk overlap (characters from previous chunk appended for context)
CHUNK_OVERLAP_CHARS = 200

# ─── Semantic Refiner (Layer 5) ───────────────────────────
# Requires GPU with CUDA
USE_GPU = True              # Toggle when running on GPU-enabled machine
REFINER_SPLIT_THRESHOLD = 0.7    # Cosine sim below this = topic shift
REFINER_MERGE_THRESHOLD = 0.95   # Cosine sim above this = merge adjacent
REFINER_BATCH_SIZE = 32          # Embedding batch size on GPU (lowered for 16GB VRAM)

# ─── LLM Services (Layers 2, 3, 6) ────────────────────────
USE_LLM = True              # Toggle when LLM API available
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL   = os.getenv("LLM_MODEL", "")

# ─── Contextual Enhancer (Layer 6) ────────────────────────
# Requires USE_LLM=True
ENHANCER_BATCH_SIZE = 10     # Chunks per LLM call
ENHANCER_MAX_CHARS  = 600    # Max chars from chunk sent to LLM for context

# ─── Qdrant (replaces ChromaDB) ────────────────────────────
QDRANT_URL        = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "storytelling_books")
