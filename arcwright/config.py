"""Configuration for Arcwright pipeline."""
import os
from pathlib import Path

# Project root (2 levels up from this file = arcwright/ → Arcwright/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directories
OUTPUT_DIR = PROJECT_ROOT / "output"
CHROMA_DIR = OUTPUT_DIR / "chroma_db"

# Ensure output dirs exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Temporary upload directory
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Models (all free, open source, run on CPU)
EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

# Chunking defaults
CHUNK_MIN_CHARS = 100
CHUNK_MAX_CHARS = 4000

# ChromaDB
CHROMA_COLLECTION_PREFIX = "arcwright_"
