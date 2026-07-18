# Arcwright — Storytelling AI Multi-Agent System 🎭

> **Main Project:** Storytelling AI — Multi-agent narrative system  
> **Side Project:** PDF Intelligence Pipeline (RAG system) at `forge/`

---

## 📊 Project Status (18 Juli 2026)

```
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  RAG Knowledge Base     (26+ books processed, 9270 chunks)
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  Agent Implementation    (8/8 agents built)
▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░  Frontend/API            (FastAPI + Web UI working)
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  Documentation           (9 docs complete)
```

---

## 🧭 Project Overview

Arcwright is a **multi-agent AI system** that helps people discover, develop, and write compelling stories from their everyday life moments.

**How it works:**
1. 🗣️ A conversational **Story Miner** asks smart questions to uncover hidden stories
2. 📚 A **RAG Librarian** queries a Qdrant vector store of 26+ storytelling books
3. 🌐 A **Web Researcher** finds real-time trending narrative techniques
4. ✅ A **Validator** scores story quality using 5 criteria
5. 🔍 A **Deep Dive** agent explores multiple perspectives
6. 📝 An **Outline Writer** structures the narrative
7. 🎬 A **Script Writer** generates the final narrative script

**Tech Stack:** Python 3.12, LangGraph (orchestration), Qdrant (vector store), BGE-M3 (embeddings), FastAPI (backend), React+Vite (frontend)

---

## 📦 Project Structure

```
Arcwright/
├── agents/                   ← ✅ LangGraph agent definitions
│   ├── state.py
│   ├── story_director.py
│   ├── story_miner.py
│   ├── rag_librarian.py
│   ├── web_researcher.py
│   ├── validator.py
│   ├── deep_dive.py
│   ├── outline_writer.py
│   └── script_writer.py
│
├── graph/                    ← ✅ LangGraph pipeline
│   ├── pipeline.py
│   └── edges.py
│
├── forge/                    ← ✅ RAG Pipeline (Existing)
│   ├── arcwright/            ← Python package (extract, chunk, embed, pipeline)
│   │   ├── extract.py
│   │   ├── chunk.py
│   │   ├── embed.py
│   │   └── pipeline.py
│   ├── api/                  ← FastAPI backend
│   ├── frontend/             ← React + Vite frontend
│   ├── data/                 ← PDF books & extracted markdown
│   └── output/               ← RAG Pipeline Output
├── qdrant_storage/           ← ✅ Qdrant Vector store data
│
├── docs/                     ← ✅ Project Documentation (9 files)
│   ├── 2026-07-10-arcwright-deep-research.md
│   ├── 2026-07-10-arcwright-pla.md
│   ├── 2026-07-10-arcwright-prd.md
│   ├── 2026-07-10-arcwright-technical-architecture.md
│   ├── 2026-07-08-storytelling-ai-agent-roles.md
│   ├── 2026-07-08-multi-agent-best-practices.md
│   ├── 2026-07-08-multi-agent-ai-architecture-patterns.md
│   ├── 2026-07-08-agentic-frameworks-research.md
│   └── RAG list of Book.md
│
├── config/                   ← ✅ Configuration files
│
├── tests/                    ← 🔜 Test suite (coming soon)
│
├── AGENTS.md                 ← AI agent instructions
├── README.md                 ← This file
├── setup.sh                  ← Environment setup
└── requirements.txt          ← Python dependencies
```

---

## ✅ What's Complete

- **RAG Pipeline** — `forge/` has full document extraction → chunking → embedding pipeline
- **Multi-Format Support** — PDF, EPUB, MOBI, AZW3, DOCX, TXT, HTML (v1.1.0)
- **26+ Books Processed** — 9,270 chunks extracted and embedded into Qdrant
- **8 Agent Roles Implemented** — including Story Miner, RAG Librarian, Validator, etc.
- **FastAPI + SSE** — Backend for real-time streaming to the UI
- **Deep Research** — validated LangGraph as framework (score 9.6/10)
- **Webtoon Case Study** — real-world validation: public company uses LangGraph for storytelling AI
- **PLA + PRD + Tech Arch** — implementation plan, product requirements, and technical specification

---

## 🔄 What's Next

### Phase 1: Complete RAG (✅ Completed)
- [x] Batch-process remaining 28 storytelling books through forge pipeline
- [x] Verify chunk quality and embedding accuracy
- [x] Set up unified Qdrant collection

### Phase 2: Build LangGraph Agents (✅ Completed)
- [x] RAG Librarian Agent (first — connects to Qdrant)
- [x] Story Miner Agent (conversational interviewer)
- [x] Web Researcher Agent (trends search)
- [x] Deep Dive Agent (perspective analysis)
- [x] Validator Agent (quality gate + debate)
- [x] Outline Writer Agent
- [x] Script Writer Agent (with self-refine)
- [x] Story Director Supervisor (orchestrator)

### Phase 3: Polish & Productionize (In Progress)
- [ ] Fix Debate loop bypassing in Validator
- [x] CLI interface
- [x] Extend FastAPI backend
- [ ] Extend React frontend (currently intro animation only)
- [ ] Hardening for production

---

## 🚀 Quick Start

```bash
# 1. Activate virtual environment
cd ~/Arcwright
source venv/bin/activate

# 2. Start RAG API (existing forge)
python forge/api/main.py
# → http://localhost:8765

# 3. Start frontend (separate terminal)
cd ~/Arcwright/forge/frontend
npm run dev
# → http://localhost:5173
```

---

## 📁 Reference Documents

All project documentation is in `docs/`:

| Document | Description |
|----------|-------------|
| `2026-07-10-arcwright-deep-research.md` | 🔬 Hermes Stack research + Webtoon case study |
| `2026-07-10-arcwright-pla.md` | 🏗️ Implementation plan (3 phases, 27 tasks) |
| `2026-07-10-arcwright-prd.md` | 📋 Product requirements (20 user stories) |
| `2026-07-10-arcwright-technical-architecture.md` | ⚙️ Full technical specification |
| `2026-07-08-storytelling-ai-agent-roles.md` | 🎭 8 agent roles & permission tiers |
| `2026-07-08-multi-agent-best-practices.md` | 🧠 Debate protocols & memory architecture |
| `2026-07-08-multi-agent-ai-architecture-patterns.md` | 🏛️ Framework comparison (LangGraph 9.6/10) |
| `2026-07-08-agentic-frameworks-research.md` | 🔬 LangGraph vs CrewAI vs AutoGen deep-dive |
| `RAG list of Book.md` | 📚 29 storytelling books for RAG |

---

## ⏰ Deadline

**Target: 31 Juli 2026** — Working prototype with all 8 agents + complete RAG.

---

*Built with ❤️ — Arcwright by roisanwr*
