# Project: Arcwright

## Overview
Storytelling AI — RAG Knowledge Base processing pipeline.
Multi-agent storytelling system powered by LangGraph + RAG.
This project uses IBM Bob as the primary development agent.

## Tech Stack
- Python 3.12
- LangGraph (agent orchestration)
- ChromaDB (vector database)
- Marker-pdf (PDF extraction)
- Sentence-transformers (embeddings)

## Coding Standards
- Follow PEP 8 with 4-space indentation
- Use type hints for all function signatures
- Document public APIs with docstrings
- Keep functions focused — one responsibility per function
- Use f-strings for string formatting
- Prefer pathlib over os.path for file operations

## Project Structure
```
Arcwright/
├── data/
│   ├── books/              ← PDF source files
│   ├── extracted/          ← OCR output (markdown)
│   └── chunks.json         ← RAG-ready chunks
├── src/
│   ├── 01-extract-pdf.py   ← PDF → Markdown
│   ├── 02-chunk-markdown.py← Markdown → Chunks
│   └── 03-embed-and-test.py ← Embed → ChromaDB
├── chroma_db/              ← Vector database (generated)
└── .bob/                   ← Bob configuration
```

## Git Workflow
- Feature branches for new work
- Conventional commit messages (feat:, fix:, refactor:, docs:, chore:)
- Keep commits focused and atomic
- Squash WIP commits before merging

## Testing
- Run tests before every commit
- Verify ChromaDB query results after embedding changes
