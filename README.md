# Arcwright — Storytelling AI Multi-Agent System 🎭

> **Main Project:** Storytelling AI — Multi-agent narrative system  
> **Side Project:** PDF Intelligence Pipeline (RAG system) at `forge/`

---

## 📊 Project Status (10 Juli 2026)

```
▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░  RAG Knowledge Base     (1/29 books processed)
▓▓▓░░░░░░░░░░░░░░░░  Agent Implementation    (0/8 agents built)
▓░░░░░░░░░░░░░░░░░░  Frontend/API            (Existing forge extended)
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░  Documentation           (9 docs complete)
```

---

## 🧭 Project Overview

Arcwright is a **multi-agent AI system** that helps people discover, develop, and write compelling stories from their everyday life moments.

**How it works:**
1. 🗣️ A conversational **Story Miner** asks smart questions to uncover hidden stories
2. 📚 A **RAG Librarian** queries a ChromaDB vector store of 29+ storytelling books
3. 🌐 A **Web Researcher** finds real-time trending narrative techniques
4. ✅ A **Validator** scores story quality using 5 criteria
5. 🔍 A **Deep Dive** agent explores multiple perspectives
6. 📝 An **Outline Writer** structures the narrative
7. 🎬 A **Script Writer** generates the final narrative script

**Tech Stack:** Python 3.12, LangGraph (orchestration), ChromaDB (vector store), BGE-M3 (embeddings), FastAPI (backend), React+Vite (frontend)

---

## 📦 Project Structure

```
Arcwright/
├── agents/                   ← 🔜 LangGraph agent definitions (coming soon)
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
├── graph/                    ← 🔜 LangGraph pipeline (coming soon)
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
│   └── output/chroma_db/     ← Vector store (to be populated)
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
├── config/                   ← 🔜 Configuration files (coming soon)
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
- **1 Book Processed** — Robert McKee's *Story* (327 chunks extracted)
- **8 Agent Roles Designed** — detailed permission tiers, debate protocols, and pipeline flow
- **Deep Research** — validated LangGraph as framework (score 9.6/10)
- **Webtoon Case Study** — real-world validation: public company uses LangGraph for storytelling AI
- **PLA + PRD + Tech Arch** — implementation plan, product requirements, and technical specification

---

## 🔄 What's Next

### Phase 1: Complete RAG (1-2 days)
- [ ] Batch-process remaining 28 storytelling books through forge pipeline
- [ ] Verify chunk quality and embedding accuracy
- [ ] Set up unified ChromaDB collection

### Phase 2: Build LangGraph Agents (8-10 days)
- [ ] RAG Librarian Agent (first — connects to ChromaDB)
- [ ] Story Miner Agent (conversational interviewer)
- [ ] Web Researcher Agent (trends search)
- [ ] Deep Dive Agent (perspective analysis)
- [ ] Validator Agent (quality gate + debate)
- [ ] Outline Writer Agent
- [ ] Script Writer Agent (with self-refine)
- [ ] Story Director Supervisor (orchestrator)

### Phase 3: Polish & Productionize (5-7 days)
- [ ] Error handling & retry logic
- [ ] LangSmith observability
- [ ] CLI interface
- [ ] Extend FastAPI backend
- [ ] Extend React frontend
- [ ] Documentation

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
