# Arcwright Forge

**Multi-strategy document chunking engine for RAG pipelines.**

Extract, clean, analyze, chunk, refine, and enhance documents — from PDFs and EPUBs to plain text — with GPU acceleration and optional LLM intelligence.

## Features

- **8-stage pipeline**: Extract → Cleanup → Boundary → Analyze → Chunk → Refine → Enhance → Embed
- **Multi-strategy chunking**: Heading-based, hybrid, recursive — auto-selected per document
- **GPU-accelerated**: BGE-M3 embedding + semantic topic shift detection via CUDA
- **LLM-enhanced**: Strategy analysis, contextual retrieval, boundary detection
- **No eager imports**: All heavy dependencies (torch, sentence-transformers, openai) load on demand
- **Any format**: PDF (OCR), EPUB, MOBI, AZW3, DOCX, TXT, HTML

## Quick Start

```bash
# Install
pip install arcwright-forge

# Extract markdown from a PDF
arcwright extract book.pdf

# Run full pipeline (cleanup → chunk → embed)
arcwright run book.pdf

# Full pipeline with GPU refinement + LLM enhancement
arcwright run book.pdf --h4 --refine --enhance --gpu --llm
```

## CLI Reference

### `arcwright run <file>`

Run the full 8-stage pipeline on a document.

| Flag | Description |
|------|-------------|
| `--h4` | Enable H4 heading boundaries |
| `--refine` | GPU semantic refinement (split/merge by topic) |
| `--enhance` | LLM contextual enhancement per chunk |
| `--no-boundary` | Disable foreword/appendix detection |
| `--no-strategy` | Disable strategy analysis |
| `--skip-embed` | Stop after chunking (don't store to vector DB) |
| `--gpu` | Enable GPU mode (`USE_GPU=True`) |
| `--llm` | Enable LLM mode (`USE_LLM=True`) |

### `arcwright extract <file>`

Extract document to markdown only.

### `arcwright chunk <file>`

Cleanup + chunk (stop before embedding).

### `arcwright refine [--book ...] [--save]`

Refine existing chunks with GPU semantic split/merge.

```bash
# Refine all books
arcwright refine --save --device cuda

# Refine specific book
arcwright refine --book "Hero" --save --split-threshold 0.65
```

### `arcwright stats [path]`

Show chunk statistics.

```bash
arcwright stats                    # All books in output/
arcwright stats output/Story_Genius  # Specific book
```

## Configuration

Via environment variables:

```bash
# LLM Provider (for strategy analysis + context enhancement)
export USE_LLM=True
export LLM_API_URL="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."

# GPU
export USE_GPU=True
```

Or via `arcwright/arcwright/config.py`:

```python
USE_GPU = True
USE_LLM = True
CHUNK_MIN_CHARS = 150
CHUNK_MAX_CHARS = 2500
REFINER_SPLIT_THRESHOLD = 0.7
```

## Python API

```python
from arcwright.pipeline import run_pipeline

# Full pipeline
result = run_pipeline(
    "book.pdf",
    use_h4=True,
    use_refiner=True,       # GPU
    use_enhancer=True,      # LLM
    use_strategy=True,      # Auto-detect strategy
    use_boundary=True,       # Filter foreword/index
)
```

## Architecture

```
📄  1/8 Extract     → marker-pdf / ebooklib / docx / txt
🧹  2/8 Cleanup     → regex: XML artifacts, empty headings, image refs
🚧 2.25/8 Boundary  → foreword→META, index→SKIP, chapters→CONTENT
🧠 2.5/8 Analyze    → LLM or heuristic: optimal strategy per document
✂️  3/8 Chunk       → H4-aware, overlap, post-process (merge tiny, split huge)
🎯 3.5/8 Refine     → GPU: BGE-M3 topic shift detection + similarity merge
🌟 3.75/8 Enhance   → LLM: Anthropic-style contextual retrieval
🗄️  4/8 Embed      → BGE-M3 1024-d vectors → ChromaDB / Qdrant
```

## Dependencies

Core (`pip install arcwright-forge`):
- sentence-transformers, chromadb, numpy, scikit-learn

Optional:
- `pip install arcwright-forge[gpu]` — adds torch (CUDA)
- `pip install arcwright-forge[llm]` — adds openai client
- `pip install arcwright-forge[extract]` — adds PDF/EPUB/DOCX support
- `pip install arcwright-forge[all]` — everything

## License

MIT
