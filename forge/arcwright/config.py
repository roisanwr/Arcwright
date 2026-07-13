"""Configuration for Arcwright pipeline."""
import os
from pathlib import Path

# Project root (2 levels up from this file = arcwright/ → Arcwright/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ─── Directories ───────────────────────────────────────────
OUTPUT_DIR = PROJECT_ROOT / "output"
CHROMA_DIR = OUTPUT_DIR / "chroma_db"

# Ensure output dirs exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Temporary upload directory
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ─── Models (all free, open source) ────────────────────────
EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

# ─── Chunking:  Strategy ──────────────────────────────────
# Heading levels to treat as chunk boundaries (1=H1, 2=H2, 3=H3, 4=H4)
# Default: H1/H2/H3 only (H4 requires explicit opt-in)
CHUNK_HEADING_LEVELS = [1, 2, 3]

# Chunk size thresholds (characters)
CHUNK_MIN_CHARS = 150        # Below this → merge with neighbor
CHUNK_MAX_CHARS = 2500       # Above this → flag for semantic refiner
CHUNK_HARD_MAX_CHARS = 4000  # Absolute max — force-split at this

# Chunk overlap (characters from previous chunk appended for context)
CHUNK_OVERLAP_CHARS = 200

# ─── Semantic Refiner (Layer 5) ───────────────────────────
# Requires GPU with CUDA
USE_GPU = False              # Toggle when running on GPU-enabled machine
REFINER_SPLIT_THRESHOLD = 0.7    # Cosine sim below this = topic shift
REFINER_MERGE_THRESHOLD = 0.95   # Cosine sim above this = merge adjacent
REFINER_BATCH_SIZE = 64          # Embedding batch size on GPU

# ─── LLM Services (Layers 2, 3, 6) ────────────────────────
USE_LLM = False              # Toggle when LLM API available
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

# ─── Contextual Enhancer (Layer 6) ────────────────────────
# Requires USE_LLM=True
ENHANCER_BATCH_SIZE = 10     # Chunks per LLM call
ENHANCER_MAX_CHARS = 600     # Max chars from chunk sent to LLM for context

# ─── ChromaDB ─────────────────────────────────────────────
CHROMA_COLLECTION_PREFIX = "arcwright_"
