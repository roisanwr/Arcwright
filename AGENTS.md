# Project: Arcwright — Storytelling AI Multi-Agent System

## Overview
Multi-agent storytelling AI system powered by LangGraph + ChromaDB RAG.
Helps people discover and craft compelling stories from everyday life moments.

## Current Status (10 Juli 2026)
- RAG pipeline: ✅ `forge/` — 1/29 books processed
- Agents: ❌ Not built yet (8 agent roles designed)
- Frontend: ✅ Existing forge React+Vite
- Docs: ✅ 9 project documents in `docs/`
- Progress: Documentation phase complete. Ready for Phase 1 (batch RAG).

## Tech Stack
- Python 3.12
- LangGraph (agent orchestration) — selected via research (9.6/10)
- ChromaDB (vector database) — existing at forge/output/chroma_db/
- BGE-M3 (embeddings) — 1024-dim, local, free
- Marker-pdf (OCR/extraction)
- FastAPI (backend)
- React + Vite (frontend)

## Project Structure
```
Arcwright/
├── agents/          ← 🔜 Agent definitions
├── graph/           ← 🔜 LangGraph pipeline
├── forge/           ← ✅ RAG Pipeline (existing)
├── docs/            ← ✅ Project docs (9 files)
├── config/          ← 🔜 Configuration
├── tests/           ← 🔜 Tests
├── AGENTS.md        ← This file
└── README.md        ← Project overview + status
```

## Coding Standards
- Follow PEP 8 with 4-space indentation
- Use type hints for all function signatures
- Document public APIs with docstrings
- Keep functions focused — one responsibility per function
- Use f-strings for string formatting
- Prefer pathlib over os.path for file operations

## Git Workflow
- Feature branches for new work
- Conventional commit messages (feat:, fix:, refactor:, docs:, chore:)
- Keep commits focused and atomic
- Squash WIP commits before merging

## Testing
- Run tests before every commit
- Verify ChromaDB query results after embedding changes
- Test each agent node individually before integration
