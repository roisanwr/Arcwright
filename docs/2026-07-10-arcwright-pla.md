---
id: "202607101510"
title: "Arcwright PLA — Project Launch Architecture & Implementation Plan"
type: project
created: 2026-07-10
tags:
  - domain/ai
  - domain/programming
  - status/draft
  - hermes/auto
ai_generated: true
review_needed: true
related:
  - "[[2026-07-10-arcwright-deep-research]]"
  - "[[2026-07-08-storytelling-ai-agent-roles]]"
  - "[[2026-07-08-multi-agent-ai-architecture-patterns]]"
  - "[[2026-07-08-agentic-frameworks-research]]"
---

# 🏗️ Arcwright PLA — Project Launch Architecture & Implementation Plan

> **Project:** Storytelling AI Multi-Agent System
> **Deadline:** 31 Juli 2026
> **Framework:** LangGraph (selected via 9.6/10 weighted score)
> **Repository:** [[https://github.com/roisanwr/Arcwright]]
> **RAG Engine:** Arcwright Forge (ChromaDB + BGE-M3)
> **Connects to:** [[2026-07-10-arcwright-deep-research]], [[2026-07-08-storytelling-ai-agent-roles]]

---

## 🎯 Project Overview

Membangun **multi-agent orchestration system** yang membantu orang menemukan, merangkai, dan menghasilkan naskah cerita dari momen-momen kecil dalam kehidupan sehari-hari.

### Core Value Proposition
> "Everyone has a story. Most people just don't know it yet."

### Target Users
- Orang biasa yang ingin bercerita tapi bingung mulai dari mana
- Content creator yang kehabisan ide cerita relatable
- Siapa pun yang ingin mengabadikan momen dalam bentuk narrative

---

## 🗺️ Implementation Roadmap (3 Fase)

### Fase 1: Foundation — RAG Pipeline Completion (Days 1-7)
**Goal:** Complete the Arcwright Forge RAG with all 29 storytelling books

| Task | Description | Est. Time | Dependencies |
|------|-------------|-----------|-------------|
| 1.1 | Batch-process remaining 28 PDFs through forge pipeline | 2 days | PDF files available |
| 1.2 | Verify chunk quality & embedding accuracy | 1 day | 1.1 done |
| 1.3 | Build RAG query testing suite (10 test queries) | 1 day | 1.2 done |
| 1.4 | Set up ChromaDB collection per book + cross-collection search | 1 day | 1.1 done |
| 1.5 | Write integration test: forge → ChromaDB → query result | 1 day | 1.3, 1.4 done |
| 1.6 | Performance benchmark: query latency, recall, relevance | 1 day | 1.5 done |

**Deliverable:** Fully functional RAG pipeline with 29 books indexed and queryable

---

### Fase 2: Core — LangGraph Multi-Agent System (Days 8-18)
**Goal:** Build all 8 agents + Story Director orchestrator

#### Week 1: Agent Implementation (Days 8-13)

| Task | Description | Est. Time |
|------|-------------|-----------|
| 2.1 | Project scaffold: LangGraph project structure, config, dependencies | 0.5 day |
| 2.2 | **RAG Librarian Agent** — connect to forge ChromaDB as tool | 1 day |
| 2.3 | **Story Miner Agent** — conversational interview loop, no external tools | 1 day |
| 2.4 | **Web Researcher Agent** — Tavily/Serper web search tool | 0.5 day |
| 2.5 | **Deep Dive Agent** — multi-perspective analysis with constrained web access | 1 day |
| 2.6 | **Validator Agent** — scoring system + debate with Story Miner | 1 day |
| 2.7 | **Outline Writer Agent** — synthesize inputs into structured outlines | 1 day |
| 2.8 | **Script Writer Agent** — expand outline to full narrative with self-refine | 1 day |

#### Week 2: Orchestration & Integration (Days 14-18)

| Task | Description | Est. Time |
|------|-------------|-----------|
| 2.9 | **Story Director (Supervisor)** — routing logic, state machine, conditional edges | 1 day |
| 2.10 | State schema design — `SessionState`, `AgentState`, `OutputState` | 0.5 day |
| 2.11 | Inter-agent communication protocol — shared state + agent_notes board | 0.5 day |
| 2.12 | Debate protocol implementation — Validator↔Story Miner loop (max 3 rounds) | 1 day |
| 2.13 | Human-in-the-loop — `interrupt()` after Outline phase for user approval | 0.5 day |
| 2.14 | Session persistence — SQLite checkpointer + thread_id management | 0.5 day |
| 2.15 | End-to-end integration test — full pipeline from user input to script output | 1 day |

**Deliverable:** Working LangGraph multi-agent system with all 8 agents orchestrated by Story Director

---

### Fase 3: Polish & Productionize (Days 19-27)
**Goal:** Production-ready system with monitoring, error handling, and UX

| Task | Description | Est. Time |
|------|-------------|-----------|
| 3.1 | Error handling — agent failure fallback, retry logic, graceful degradation | 1 day |
| 3.2 | Inter-agent message logging — every handoff logged with content validation | 1 day |
| 3.3 | Context window monitoring — track utilization per agent | 1 day |
| 3.4 | Cost tracking — per-agent token consumption | 0.5 day |
| 3.5 | LangSmith observability — traces, debugging, latency tracking | 0.5 day |
| 3.6 | CLI interface — simple terminal-based user interaction | 1 day |
| 3.7 | Output formatting — clean markdown output with platform variants | 1 day |
| 3.8 | User feedback loop — improve agent behavior based on ratings | 1 day |
| 3.9 | Documentation — README, API docs, agent roles guide | 1 day |
| 3.10 | Performance optimization — reduce latency, parallelize where possible | 1 day |

**Deliverable:** Production-ready system that can be deployed and run end-to-end

---

## 🧠 Agent Architecture (Refined)

### State Schema Design

```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from datetime import datetime

class UserProfile(TypedDict):
    name: str
    platform_target: Literal["youtube", "tiktok", "podcast", "blog", "general"]
    session_count: int
    preferred_language: str

class StoryFragment(TypedDict):
    id: str
    text: str
    emotion: str | None
    timestamp: str

class AgentNote(TypedDict):
    agent_name: str
    note_type: Literal["question", "insight", "flag", "suggestion"]
    content: str

class ValidationResult(TypedDict):
    score: float  # 0-10
    criteria_scores: dict[str, float]
    feedback: str
    passed: bool

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

# Main session state
class ArcwrightState(TypedDict):
    # Metadata
    session_id: str
    current_phase: Literal["mining", "enriching", "validating", "outlining", "scripting", "complete"]
    
    # User context
    user_profile: UserProfile
    messages: Annotated[list, add_messages]  # Chat history
    
    # Story discovery
    story_fragments: Annotated[list[StoryFragment], lambda a, b: a + b]
    interview_questions_asked: Annotated[list[str], lambda a, b: a + b]
    
    # Agent communication board
    agent_notes: Annotated[list[AgentNote], lambda a, b: a + b]
    
    # Knowledge enrichment
    rag_context: list[dict]        # Latest RAG results
    web_research: list[dict]       # Latest web research
    deep_dive_analysis: dict       # Multi-perspective analysis
    
    # Validation
    validation_result: ValidationResult | None
    debate_rounds: int
    debate_log: Annotated[list[dict], lambda a, b: a + b]
    
    # Output
    story_outline: StoryOutline | None
    output_script: OutputScript | None
    
    # Controls
    outline_approved: bool
    user_interrupt_pending: bool
    error_count: int
```

### Permission Tier Matrix

| Agent | Layer | User Chat | RAG DB | Web Search | Write State | Read State | Debate |
|-------|-------|:---------:|:------:|:----------:|:-----------:|:----------:|:------:|
| **Story Director** | Orchestrator | ✅ Interrupt only | ❌ | ❌ | ✅ Full | ✅ Full | ✅ Arbitrator |
| **Story Miner** | Layer 1 | ✅ Full | ❌ | ❌ | ❌ | ✅ Read | ✅ Proposer |
| **RAG Librarian** | Layer 1 | ❌ | ✅ Full | ❌ | ❌ | ✅ Read (fragments) | ❌ |
| **Web Researcher** | Layer 1 | ❌ | ❌ | ✅ Full | ❌ | ✅ Read (context) | ❌ |
| **Validator** | Layer 2 | ❌ | ✅ Read | ❌ | ✅ Validation result | ✅ Full | ✅ Critic |
| **Deep Dive** | Layer 2 | ❌ | ✅ Read | ✅ Throttled | ✅ Analysis | ✅ Full | ❌ |
| **Outline Writer** | Layer 3 | ❌ | ✅ Read | ❌ | ✅ Outline | ✅ Full | ❌ |
| **Script Writer** | Layer 3 | ❌ | ✅ Read | ❌ | ✅ Script | ✅ Approved outline only | ❌ |

### Flow Pipeline

```
[USER INPUT] → "aku gak tau mau cerita apa"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ STORY DIRECTOR                                               │
│ • Classify intent → "discovery mode"                         │
│ • Initialize session state                                   │
│ • Route to Story Miner                                       │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ STORY MINER ↔ RAG LIBRARIAN                                  │
│ • Interactive Q&A session (2-5 rounds)                       │
│ • RAG supplies smart questions from storytelling books       │
│ • Extract: themes, emotions, characters, moments             │
│ • Store fragments in session state                           │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ STORY DIRECTOR — detect enough material?                     │
│ If NO → loop back to Story Miner with new angles             │
│ If YES → route to Deep Dive + Web Researcher (parallel)     │
└─────────────────────────────────────────────────────────────┘
    │  Send() to both simultaneously
    ├──▶ DEEP DIVE AGENT — multi-perspective analysis
    │    • Surface → Psychological → Universal → Opposing → Hidden Gold
    │
    └──▶ WEB RESEARCHER — real-time trends
         • Audience intelligence, platform fit, relatable themes
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ OUTLINE WRITER                                               │
│ • Synthesize all inputs                                     │
│ • Generate 2-3 outline variants                              │
│ • Apply story framework from RAG                            │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ VALIDATOR ↔ STORY MINER (Debate Loop)                        │
│ • Validator scores: Relatability, Emotional Hook,            │
│   Originality, Platform Fit, Trend Alignment                 │
│ • < 25/50 → Reject → story_miner loop                       │
│ • 25-34 → Revise with specific feedback                      │
│ • >= 35 → Pass                                              │
│ • Max 3 debate rounds → Story Director arbitrates           │
└─────────────────────────────────────────────────────────────┘
    │ PASS
    ▼
┌─────────────────────────────────────────────────────────────┐
│ STORY DIRECTOR → interrupt() → USER                          │
│ "Here's your outline. Approve or request changes?"           │
│ If APPROVE → route to Script Writer                          │
│ If REVISE → loop back to Outline Writer / Story Miner       │
└─────────────────────────────────────────────────────────────┘
    │ APPROVED
    ▼
┌─────────────────────────────────────────────────────────────┐
│ SCRIPT WRITER                                                │
│ • Generate full narrative script                             │
│ • Self-refine loop (1-2 internal iterations)                 │
│ • Platform-specific formatting                               │
│ • Voice matching from session data                           │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
[FINAL OUTPUT: Naskah Siap Pakai] ✅
```

---

## 🛠️ Tech Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | LangGraph | v0.4+ | Agent orchestration |
| **LLM** | GPT-4o / Claude Sonnet | Latest | Agent reasoning |
| **RAG DB** | ChromaDB | v0.6+ | Vector storage |
| **Embeddings** | BGE-M3 (BAAI) | Latest | 1024-dim vector |
| **Web Search** | Tavily / Serper | API | Real-time research |
| **PDF Pipeline** | marker-pdf + Surya | Latest | OCR extraction |
| **Persistence** | SQLite | Built-in | Session checkpointing |
| **Observability** | LangSmith | Free tier | Tracing, debugging |
| **Interface** | CLI (initial) | — | User interaction |
| **Package** | LangChain | v0.3+ | Chroma integration |

### Directory Structure

```
~/Arcwright/
├── forge/                      ← Existing RAG pipeline
│   └── output/chroma_db/       ← Vector store (29 books)
├── agents/                     ← NEW: LangGraph agents
│   ├── __init__.py
│   ├── state.py                ← ArcwrightState schema
│   ├── story_director.py       ← Supervisor orchestrator
│   ├── story_miner.py          ← Layer 1: Interactive miner
│   ├── rag_librarian.py        ← Layer 1: RAG retriever
│   ├── web_researcher.py       ← Layer 1: Web search
│   ├── validator.py            ← Layer 2: Quality gate
│   ├── deep_dive.py            ← Layer 2: Perspective analysis
│   ├── outline_writer.py       ← Layer 3: Structure builder
│   └── script_writer.py        ← Layer 3: Narrative writer
├── graph/                      ← NEW: LangGraph pipeline
│   ├── __init__.py
│   ├── graph.py                ← StateGraph definition
│   ├── edges.py                ← Conditional routing
│   └── pipeline.py             ← Full pipeline orchestration
├── config/
│   ├── agents.yaml             ← Agent configurations
│   └── prompts/                ← System prompts per agent
├── main.py                     ← Entry point (CLI)
└── tests/
    ├── test_agents.py
    └── test_pipeline.py
```

---

## 🚨 Risk Register

| Risk | Probability | Impact | Mitigation |
|------|:----------:|:------:|-----------|
| **Hallucination propagation** | HIGH | HIGH | Validator at every handoff, schema validation |
| **LLM cost overrun** | MEDIUM | MEDIUM | Track per-agent tokens, optimize prompts |
| **Context window overflow** | MEDIUM | HIGH | Message trimming, summary compression |
| **Bad RAG retrieval** | LOW | MEDIUM | BGE-M3 is top-ranked; test with 29 books |
| **User disengagement** | LOW | HIGH | Keep interview under 5 rounds; engaging prompts |
| **Deadlock in debate** | LOW | MEDIUM | Max 3 rounds; Story Director arbitrates |

---

## ✅ Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| User finds a story | ≥80% of sessions produce a usable outline | Session logs |
| Outline quality (validated) | ≥35/50 validation score | Validator output |
| User approval rate | ≥70% approve outline on first pass | User interrupt outcome |
| End-to-end latency | ≤45 seconds (excluding LLM generation) | LangSmith traces |
| RAG recall | ≥85% relevant chunks for test queries | Manual review of top-5 results |
| System reliability | ≥99% pipeline completion rate | Error logs |

---

## 📈 Post-Launch Roadmap

- **Web Interface** — FastAPI + React (extend existing forge frontend)
- **Multi-language** — Support Indonesian + English (BGE-M3 supports 100+ languages)
- **Audio output** — Text-to-speech integration for podcast scripts
- **Platform publishing** — Direct publish to YouTube, TikTok, Substack
- **Memory across sessions** — User profile persistence (story preferences, past topics)
- **A/B testing** — Compare debate vs no-debate output quality

---

*Generated by Hermes (Yui) on 2026-07-10 — Based on deep research + existing vault analysis*
