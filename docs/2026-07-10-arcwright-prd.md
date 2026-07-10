---
id: "202607101520"
title: "Arcwright PRD — Product Requirements Document"
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
  - "[[2026-07-10-arcwright-pla]]"
  - "[[2026-07-08-storytelling-ai-agent-roles]]"
---

# 📋 Arcwright PRD — Product Requirements Document

> **Product:** Storytelling AI Multi-Agent System
> **Version:** 1.0 (Prototype)
> **Deadline:** 31 Juli 2026
> **Repository:** [[https://github.com/roisanwr/Arcwright]]

---

## 1. Product Overview

### 1.1 Vision
Membangun sistem AI multi-agent yang membantu **siapa pun** menemukan cerita berharga dalam kehidupan sehari-hari mereka dan mengubahnya menjadi **naskah yang siap dibagikan** — tanpa perlu keahlian menulis atau storytelling.

### 1.2 Mission Statement
> "Make every person a storyteller by unearthing the hidden narratives in their everyday life."

### 1.3 Target Audience

| Persona | Description | Pain Point | Use Case |
|---------|-------------|------------|----------|
| **Everyday Person** | Orang biasa yang merasa hidupnya "gak menarik" | Gak tahu cara bercerita; gak sadar momen berharga | "Aku pengen cerita tentang momen ini tapi gak tau caranya" |
| **Aspiring Creator** | Content creator pemula yang baru mulai | Ide cerita habis; gak tahu cara bikin konten relatable | "Gue pengen konten yang relate tapi gak tau mau cerita apa" |
| **Journal Keeper** | Orang yang suka nulis diary | Ingin menulis lebih engaging tapi stuck | "Catatan harianku pengen dijadikan cerita" |

---

## 2. User Stories

### 2.1 Discovery & Onboarding

**US-01:** As a user who doesn't know what to talk about, I want the AI to guide me with smart questions so I can discover stories I didn't realize I had.
- **Acceptance:** First session ≥70% of users produce at least one story fragment after 5 questions

**US-02:** As a user with a vague idea, I want the AI to help me refine it into a clear narrative angle.
- **Acceptance:** User rates the refined angle as "better than my original idea" ≥60%

### 2.2 Story Development

**US-03:** As a user, I want the AI to suggest storytelling frameworks (Hero's Journey, Save the Cat, etc.) that fit my story naturally.
- **Acceptance:** RAG retrieves relevant framework in ≥85% of sessions

**US-04:** As a user, I want the AI to check if my story will resonate with other people before I spend time writing it.
- **Acceptance:** Validation score of ≥35/50 before proceeding to outline

**US-05:** As a user, I want the AI to explore my story from different perspectives so I don't miss important angles.
- **Acceptance:** Deep Dive agent produces ≥3 distinct perspectives per session

### 2.3 Output Generation

**US-06:** As a user, I want to see a clear story outline before committing to the full script.
- **Acceptance:** Outline presented with hook, setup, turning point, struggle, resolution, punchline

**US-07:** As a user, I want the AI to write a full narrative script based on the approved outline.
- **Acceptance:** Script generated in ≤30 seconds after approval

**US-08:** As a user, I want the output formatted for my target platform (YouTube, TikTok, Podcast, Blog).
- **Acceptance:** At least 4 platform variants supported

### 2.4 Quality & Control

**US-09:** As a user, I want to approve the outline before the script is written, so I maintain creative control.
- **Acceptance:** Pipeline pauses at outline step; user can approve/revise/reject

**US-10:** As a user, I want the AI to learn from my feedback and improve its suggestions over time.
- **Acceptance:** Session feedback collected and stored for future reference

---

## 3. Functional Requirements

### 3.1 Agent System (Core)

| ID | Requirement | Priority | Dependencies |
|----|------------|----------|--------------|
| FR-01 | System must have a **Story Director** orchestrator that routes tasks to specialist agents | P0 | — |
| FR-02 | **Story Miner** must conduct interactive Q&A sessions (2-5 rounds) to extract story fragments | P0 | FR-01 |
| FR-03 | **RAG Librarian** must query the ChromaDB vector store for storytelling frameworks | P0 | FR-01, forge/chroma_db |
| FR-04 | **Web Researcher** must search real-time trends for audience intelligence | P1 | FR-01 |
| FR-05 | **Validator** must score outlines on 5 criteria (Relatability, Emotional Hook, Originality, Platform Fit, Trend) | P0 | FR-01 |
| FR-06 | **Deep Dive** must analyze story from ≥3 perspectives (psychological, universal theme, opposing view) | P1 | FR-01 |
| FR-07 | **Outline Writer** must produce structured outlines with hook/setup/turning point/resolution/punchline | P0 | FR-01 |
| FR-08 | **Script Writer** must generate full narrative scripts from approved outlines | P0 | FR-01, FR-07 |

### 3.2 Debate & Validation

| ID | Requirement | Priority | Dependencies |
|----|------------|----------|--------------|
| FR-09 | System must support **Validator ↔ Story Miner debate** (max 3 rounds) for outline quality | P0 | FR-05, FR-02 |
| FR-10 | Validator must use 5-criteria scoring system with ≥35/50 pass threshold | P0 | FR-09 |
| FR-11 | Story Director must arbitrate if debate reaches max rounds without consensus | P0 | FR-09, FR-01 |
| FR-12 | System must log all debate rounds with agent reasoning for audit | P1 | FR-09 |

### 3.3 Human-in-the-Loop

| ID | Requirement | Priority | Dependencies |
|----|------------|----------|--------------|
| FR-13 | Pipeline must **interrupt** and present outline to user for approval before script generation | P0 | FR-07 |
| FR-14 | User must be able to **approve, request revision, or reject** the outline | P0 | FR-13 |
| FR-15 | On revision request, system must loop back to appropriate agent with user feedback | P0 | FR-14 |
| FR-16 | User feedback must be stored in session state for downstream agents | P1 | FR-14 |

### 3.4 RAG Integration

| ID | Requirement | Priority | Dependencies |
|----|------------|----------|--------------|
| FR-17 | System must connect to existing Arcwright forge ChromaDB instance | P0 | forge functional |
| FR-18 | RAG must support query by technique type (questioning, frameworks, audience psychology) | P1 | FR-17 |
| FR-19 | RAG results must include source book title and section for traceability | P1 | FR-17 |
| FR-20 | System must process all 29 storytelling books through the RAG pipeline | P0 | forge pipeline |

### 3.5 Session Management

| ID | Requirement | Priority | Dependencies |
|----|------------|----------|--------------|
| FR-21 | Session state must persist across interruptions (crash recovery) | P0 | LangGraph checkpointer |
| FR-22 | Session must be identifiable by unique `session_id` (thread_id) | P0 | FR-21 |
| FR-23 | System must handle concurrent sessions (multiple users) | P2 | FR-21 |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement | Target | Measurement |
|----|------------|--------|-------------|
| NFR-01 | End-to-end session time (user input → script output) | ≤5 minutes | LangSmith trace |
| NFR-02 | RAG query response time | ≤2 seconds | ChromaDB metrics |
| NFR-03 | Script generation time | ≤30 seconds | Agent log |
| NFR-04 | Maximum autonomous steps before human intervention | ≤10 steps | Step counter |
| NFR-05 | System must handle ≥5 concurrent sessions | ≥5 sessions | Load test |

### 4.2 Quality

| ID | Requirement | Target | Measurement |
|----|------------|--------|-------------|
| NFR-06 | Validator-Accepted outline rate | ≥70% first pass | Session logs |
| NFR-07 | Story Miner: ≥1 story fragment per session | 100% sessions | State data |
| NFR-08 | User satisfaction rate (post-session) | ≥4/5 | User rating |
| NFR-09 | RAG relevance (top-3 results) | ≥85% relevant | Manual audit |
| NFR-10 | Hallucination rate in script output | ≤5% of claims | Spot-check |

### 4.3 Reliability

| ID | Requirement | Target | Measurement |
|----|------------|--------|-------------|
| NFR-11 | Pipeline completion rate (no crash) | ≥99% | Error logs |
| NFR-12 | Agent failure recovery | Auto-retry ≤3 attempts | Error handler |
| NFR-13 | Session state integrity | No data loss | Checkpoint verify |

---

## 5. Constraints & Boundaries

### 5.1 Technical Constraints
- **Python 3.12+** — all agents run in Python
- **Local-first** — no cloud dependency for core pipeline (except LLM API calls)
- **ChromaDB** — vector store must remain file-based (no separate server)
- **LangGraph** — all orchestration via LangGraph's StateGraph
- **BGE-M3** — embedding model for RAG (free, local)

### 5.2 What This System Will NOT Do (v1.0)
- ❌ Multi-language output (v1.0 only Indonesian + English)
- ❌ Direct social media publishing
- ❌ Voice/audio generation
- ❌ Multi-image/video processing
- ❌ Real-time collaborative editing
- ❌ Mobile app (CLI/desktop only)

---

## 6. Data Flow (High-Level)

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  USER   │───▶│  STORY   │───▶│  STORY   │───▶│ VALIDATOR│
│ INPUT   │    │ DIRECTOR │    │  MINER   │    │  DEBATE  │
└─────────┘    └──────────┘    └──────────┘    └──────────┘
                    │                │                │
                    │         ┌──────▼──────┐         │
                    │         │  RAG        │         │
                    │         │  LIBRARIAN  │         │
                    │         └─────────────┘         │
                    │                                │
                    │    ┌──────────────────────┐    │
                    ├────│  DEEP DIVE + WEB     │────│
                    │    │  RESEARCH (Parallel)  │    │
                    │    └──────────────────────┘    │
                    │                                │
                    ▼                                ▼
              ┌──────────┐                    ┌──────────┐
              │  OUTLINE  │◀───────────────────│  PASS    │
              │  WRITER   │     (if ≥35/50)    │          │
              └────┬─────┘                    └──────────┘
                   │
              ┌────▼─────┐
              │  USER     │  ← INTERRUPT: Approve outline?
              │  APPROVAL │
              └────┬─────┘
                   │ (Approved)
              ┌────▼─────┐
              │  SCRIPT   │
              │  WRITER   │
              └────┬─────┘
                   │
              ┌────▼─────┐
              │  OUTPUT   │
              │  DELIVER  │
              └──────────┘
```

---

## 7. Success Metrics (OKRs)

| Objective | Key Result | Target |
|-----------|-----------|--------|
| **Validate product-market fit** | Users who find a story in their session | ≥80% |
| **Quality bar** | Validation score ≥35/50 | ≥70% of outlines |
| **User engagement** | Sessions that complete full pipeline (input → script) | ≥50% |
| **Speed** | Total session time (excluding user thinking) | ≤5 min |
| **Accuracy** | RAG queries returning relevant results | ≥85% |

---

## 8. Open Questions

| Question | Discussion | Decision Needed By |
|----------|-----------|-------------------|
| Should we start with CLI or build web UI first? | CLI is faster to prototype; web is better UX | Phase 2 decision |
| Which LLM provider? GPT-4o vs Claude Sonnet vs local Ollama | GPT-4o for initial; can swap via config | Phase 1 start |
| How many debate rounds before arbitration? | Research says 2-3 optimal; 3 gives safety margin | Phase 2.12 |
| Should we use LangGraph's built-in supervisor or custom? | `langgraph-supervisor` package is now production-ready | Phase 2.9 |

---

*Generated by Hermes (Yui) on 2026-07-10 — Based on deep research + user requirements*
