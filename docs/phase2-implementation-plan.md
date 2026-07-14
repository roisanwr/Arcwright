# Phase 2 Implementation Plan — Arcwright LangGraph Agents

> **Status:** In Progress  
> **Goal:** Build all 8 LangGraph agents + Story Director orchestrator  
> **RAG:** ✅ 9,270 chunks dari 26 buku sudah di ChromaDB (`forge/output/chroma_db/`)  
> **Deadline:** 31 Juli 2026

---

## Overview

Membangun sistem multi-agent berbasis LangGraph yang terdiri dari 8 agent khusus yang dikoordinasi oleh Story Director. Semua agent berkomunikasi via shared state (`ArcwrightState`) — tidak ada direct agent-to-agent call.

---

## Directory Structure Target

```
Arcwright/
├── agents/
│   ├── __init__.py
│   ├── state.py              ← ArcwrightState TypedDict
│   ├── story_director.py     ← Supervisor routing node
│   ├── story_miner.py        ← Conversational interviewer
│   ├── rag_librarian.py      ← ChromaDB retriever agent
│   ├── web_researcher.py     ← Tavily web search agent
│   ├── validator.py          ← Quality gate + debate logic
│   ├── deep_dive.py          ← Multi-perspective analyst
│   ├── outline_writer.py     ← Story structure builder
│   └── script_writer.py      ← Narrative script generator
├── graph/
│   ├── __init__.py
│   ├── edges.py              ← Conditional routing functions
│   └── pipeline.py           ← StateGraph compile + checkpointer
├── config/
│   ├── __init__.py
│   └── settings.py           ← API keys, model names, paths
├── tests/
│   ├── test_state.py
│   ├── test_agents.py
│   └── test_pipeline.py
├── main.py                   ← CLI entry point
└── requirements.txt          ← langgraph, langchain, etc.
```

---

## Sub-Task Breakdown

---

### Task 2.1 — Project Scaffold
**Status:** `[ ] pending`

**Intent:** Setup semua dependencies, directories, dan config sebelum nulis satu baris agent code.

**Expected Outcomes:**
- `requirements.txt` updated dengan semua LangGraph/LangChain deps
- `config/settings.py` dengan semua env vars dan path configs
- Semua direktori (`agents/`, `graph/`, `config/`, `tests/`) sudah ada dengan `__init__.py`

**Todo List:**
1. Buat `requirements.txt` dengan deps: `langgraph>=0.4`, `langchain>=0.3`, `langchain-chroma`, `langchain-community`, `langchain-openai`, `tavily-python`, `python-dotenv`, `sentence-transformers`
2. Buat `config/settings.py` — semua config (LLM model, ChromaDB path, API keys via env)
3. Buat semua direktori + `__init__.py` files
4. Buat `.env.example` untuk dokumentasi env vars yang dibutuhkan

**Relevant Context:**
- ChromaDB path: `forge/output/chroma_db/`
- Collection name: `storytelling_books`
- Embedding model: `BAAI/bge-m3` (harus sama dengan yang dipakai saat indexing)

---

### Task 2.2 — State Schema (`agents/state.py`)
**Status:** `[ ] pending`

**Intent:** Definisikan `ArcwrightState` TypedDict yang menjadi kontrak komunikasi antar semua agent.

**Expected Outcomes:**
- `ArcwrightState` dengan semua fields yang dibutuhkan pipeline
- Reducer functions untuk list fields (append, tidak replace)
- Sub-TypedDicts: `UserProfile`, `StoryFragment`, `AgentNote`, `ValidationResult`, `StoryOutline`, `OutputScript`

**Todo List:**
1. Definisikan semua sub-TypedDicts
2. Buat `ArcwrightState` dengan `Annotated` fields untuk lists (pakai `operator.add` atau custom reducer)
3. Tambahkan `messages: Annotated[list, add_messages]` untuk LangGraph message history
4. Export semua types dari `agents/__init__.py`

**Key Design Decisions:**
- `story_fragments`, `agent_notes`, `debate_log` — pakai `Annotated[list, operator.add]` (append-only)
- `rag_context`, `web_research`, `deep_dive_analysis` — overwrite (last agent wins)
- `validation_result`, `story_outline`, `output_script` — `Optional`, overwrite
- `debate_rounds: int` — increment setiap round, Story Director reset ke 0 kalau phase berganti

---

### Task 2.3 — RAG Librarian Agent (`agents/rag_librarian.py`)
**Status:** `[ ] pending`

**Intent:** Koneksikan ke ChromaDB Forge yang sudah ada, buat sebagai LangChain retriever tool yang bisa di-query oleh agent.

**Expected Outcomes:**
- Agent bisa query ChromaDB dengan BGE-M3 embeddings (SAMA dengan yang dipakai saat indexing)
- Hasil retrieval disimpan ke `state["rag_context"]` dengan source attribution
- MMR search untuk diversity (k=5, fetch_k=20)

**Todo List:**
1. Load ChromaDB dari `forge/output/chroma_db/` dengan `chromadb.PersistentClient`
2. Inisialisasi `HuggingFaceEmbeddings(model_name="BAAI/bge-m3")` — **wajib sama persis dengan forge**
3. Buat `Chroma` LangChain wrapper dengan collection `storytelling_books`
4. Buat `create_retriever_tool` dengan deskripsi yang jelas
5. Buat `create_react_agent` dengan system prompt RAG Librarian
6. Buat wrapper node function `rag_librarian_node(state) -> dict`

**Relevant Context:**
- Lihat `forge/arcwright/embed.py` untuk config embedding yang tepat
- Collection name: `storytelling_books`
- Search type: MMR untuk diversity
- **Jangan** gunakan `OpenAIEmbeddings` — harus BGE-M3 karena database sudah di-embed dengan itu

---

### Task 2.4 — Story Miner Agent (`agents/story_miner.py`)
**Status:** `[ ] pending`

**Intent:** Conversational agent yang meng-interview user untuk extract story fragments. No external tools — pure LLM conversation.

**Expected Outcomes:**
- Agent bisa conduct Q&A yang engaging dan empathetic
- Story fragments di-extract dan disimpan ke `state["story_fragments"]`
- Bisa menerima feedback dari Validator (via `agent_notes`) untuk drill deeper

**Todo List:**
1. Buat `create_react_agent` dengan tools=[] (pure conversation)
2. Tulis system prompt: empathetic interviewer, 1 question at a time, extract fragments
3. Buat wrapper `story_miner_node(state) -> dict` yang parse output dan update fragments
4. Handle "debate mode": kalau ada Validator critique di `agent_notes`, address it

**System Prompt Key Points:**
- Ask ONE question at a time, never multiple
- Start broad, drill into sensory/emotional specifics
- Extract: theme, emotion, character, conflict, specific moment
- After 2-3 solid fragments, signal ready for next phase
- Kalau ada critique dari Validator di `agent_notes`, re-interview dengan angle baru

---

### Task 2.5 — Web Researcher Agent (`agents/web_researcher.py`)
**Status:** `[ ] pending`

**Intent:** Search real-time trends via Tavily untuk audience intelligence dan platform fit.

**Expected Outcomes:**
- Agent bisa search trends berdasarkan story fragments
- Hasil disimpan ke `state["web_research"]` dengan source URLs
- Berjalan parallel dengan Deep Dive via `Send()`

**Todo List:**
1. Install dan setup `TavilySearchResults` tool (via `langchain-community`)
2. Buat `create_react_agent` dengan Tavily tool
3. Tulis system prompt: trend scout, audience intelligence, platform-specific research
4. Buat wrapper `web_researcher_node(state) -> dict`

**Note:** Kalau `TAVILY_API_KEY` tidak ada, gracefully fallback ke empty `web_research: []`.

---

### Task 2.6 — Deep Dive Agent (`agents/deep_dive.py`)
**Status:** `[ ] pending`

**Intent:** Analisis story dari 5 perspektif berbeda untuk uncover hidden angles.

**Expected Outcomes:**
- Output: `deep_dive_analysis` dict dengan 5 perspektif: surface, psychological, universal, opposing, hidden_gold
- Berjalan parallel dengan Web Researcher

**Todo List:**
1. Buat `create_react_agent` dengan RAG tool (read-only, untuk framework reference)
2. Tulis system prompt dengan strict output format (5 perspectives)
3. Buat wrapper `deep_dive_node(state) -> dict` yang parse 5 perspectives
4. Pastikan output structured: `{"surface": "...", "psychological": "...", "universal": "...", "opposing": "...", "hidden_gold": "..."}`

---

### Task 2.7 — Validator Agent (`agents/validator.py`)
**Status:** `[ ] pending`

**Intent:** Quality gate yang score outline pada 5 kriteria dan bisa engage dalam debate dengan Story Miner.

**Expected Outcomes:**
- Score outline 0-50 (5 kriteria × 0-10)
- Output structured `ValidationResult` ke `state["validation_result"]`
- Bisa provide critique yang actionable untuk debate

**Todo List:**
1. Buat `create_react_agent` dengan system prompt yang strict tentang scoring rubric
2. Definisikan scoring criteria: Relatability, Emotional Hook, Originality, Platform Fit, Trend Alignment
3. Buat wrapper `validator_node(state) -> dict` yang parse score dari LLM output
4. Tulis critique ke `agent_notes` supaya Story Miner bisa baca

**Scoring Thresholds:**
- `≥35/50` → PASS
- `25-34` → REVISE (debate round)
- `<25` → REJECT (loop ke Story Miner)
- `debate_rounds >= 3` → Story Director arbitrates

---

### Task 2.8 — Outline Writer Agent (`agents/outline_writer.py`)
**Status:** `[ ] pending`

**Intent:** Synthesize semua inputs (fragments + RAG + web research + deep dive) menjadi structured outline.

**Expected Outcomes:**
- Output: `StoryOutline` ke `state["story_outline"]` dengan semua 7 fields
- Gunakan RAG context untuk apply storytelling framework yang relevan

**Todo List:**
1. Buat `create_react_agent` dengan system prompt yang menekankan synthesis
2. Tulis output format yang explicit: title, hook, setup, turning_point, struggle, resolution, punchline, platform, estimated_duration
3. Buat wrapper `outline_writer_node(state) -> dict` yang parse JSON output ke `StoryOutline`

---

### Task 2.9 — Script Writer Agent (`agents/script_writer.py`)
**Status:** `[ ] pending`

**Intent:** Generate full narrative script dari approved outline. Only runs setelah user approval.

**Expected Outcomes:**
- Full narrative script tersimpan di `state["output_script"]`
- Platform-specific formatting (YouTube/TikTok/Podcast/Blog)
- Self-refine loop (1-2 internal iterations via LLM)

**Todo List:**
1. Buat `create_react_agent` dengan RAG tool (untuk dialogue techniques)
2. Tulis system prompt: narrative poet, match user voice, platform-aware
3. Tambahkan self-refine: generate → critique → refine (dalam 1 node, 2 LLM calls max)
4. Buat wrapper `script_writer_node(state) -> dict`

**Safety Gate:** Node ini harus check `state["outline_approved"] == True` sebelum jalan. Kalau tidak, return error.

---

### Task 2.10 — Story Director + Routing (`agents/story_director.py` + `graph/edges.py`)
**Status:** `[ ] pending`

**Intent:** Supervisor yang mengontrol alur pipeline — memutuskan agent mana yang jalan berikutnya berdasarkan state.

**Expected Outcomes:**
- `story_director_node` yang update `current_phase` berdasarkan kondisi state
- `story_director_routing` function yang return nama node berikutnya
- `validator_debate_routing` function untuk debate loop logic
- Parallel execution Deep Dive + Web Researcher via `Send()`

**Todo List:**
1. Buat `story_director_node(state) -> dict` — update phase, check conditions
2. Buat `story_director_routing(state) -> str` — pure routing logic
3. Buat `validator_debate_routing(state) -> str` — debate scoring logic
4. Buat parallel dispatch: kalau phase == "enriching" dan fragments cukup → `Send()` ke deep_dive DAN web_researcher

**Routing Logic:**

```
"mining" phase:
  fragments < 2 AND no rag_context  → "rag_librarian"
  fragments < 2 AND has rag_context → "story_miner"
  fragments >= 2                    → update phase → "enriching"

"enriching" phase:
  no deep_dive_analysis → parallel Send(["deep_dive", "web_researcher"])
  has analysis, no outline → "outline_writer"
  has outline, no validation → "validator"

"validating" phase:
  passed                → update phase → "outlining" → "user_approval"
  failed + rounds < 3   → "story_miner" (debate)
  failed + rounds >= 3  → Story Director arbitrates → "outline_writer"

"scripting" phase:
  outline_approved == True → "script_writer"
  outline_approved == False → "user_approval"

"complete" → END
```

---

### Task 2.11 — Graph Pipeline (`graph/pipeline.py`)
**Status:** `[ ] pending`

**Intent:** Compile StateGraph dengan semua nodes, edges, checkpointer, dan interrupt configuration.

**Expected Outcomes:**
- `create_arcwright_graph()` function yang return compiled graph
- `SqliteSaver` checkpointer untuk persistence
- `interrupt_before=["user_approval"]` untuk HITL pause
- Parallel edges untuk Deep Dive + Web Researcher

**Todo List:**
1. Import semua agent nodes
2. Register semua nodes ke `StateGraph(ArcwrightState)`
3. Add edges: semua agent → story_director (kecuali script_writer → END)
4. Add conditional edges dari story_director dan validator
5. Compile dengan `SqliteSaver` checkpointer dan `interrupt_before=["user_approval"]`

**Key LangGraph patterns:**
- `builder.add_conditional_edges("story_director", story_director_routing, {...})`
- `builder.add_conditional_edges("validator", validator_debate_routing, {...})`
- Parallel: di story_director_routing, return `[Send("deep_dive", state), Send("web_researcher", state)]` untuk parallel execution

---

### Task 2.12 — Human-in-the-Loop Node (`agents/story_director.py`)
**Status:** `[ ] pending`

**Intent:** Implementasi `user_approval_node` yang pause pipeline dan tunggu user input.

**Expected Outcomes:**
- Pipeline pause setelah outline selesai divalidasi
- User bisa: approve, request revision, atau reject
- Resume dengan `Command(resume=decision)` dari CLI

**Todo List:**
1. Buat `user_approval_node(state)` yang call `interrupt(outline_dict)` 
2. Handle 3 responses: `"approve"` → set `outline_approved=True`, `"revise"` → loop back, `"reject"` → loop ke story_miner
3. Format outline yang dikirim ke user: readable dan clean

---

### Task 2.13 — CLI Entry Point (`main.py`)
**Status:** `[ ] pending`

**Intent:** Simple terminal interface untuk run full pipeline.

**Expected Outcomes:**
- User bisa start session via `python main.py`
- Multi-turn conversation loop
- Handle interrupt (outline approval) dengan user input
- Session persistence via thread_id

**Todo List:**
1. Buat interactive loop: input user → invoke graph → check interrupt → output
2. Handle `__interrupt__` key di response: display outline, ask for approval
3. Handle `Command(resume=...)` untuk resume setelah approval
4. Display final script dengan formatting yang clean
5. Save session ID untuk resume capability

---

### Task 2.14 — Integration Test
**Status:** `[ ] pending`

**Intent:** End-to-end test dari user input hingga script output.

**Expected Outcomes:**
- Test dengan dummy story fragments (tanpa LLM untuk speed)
- Test routing logic (mock LLM responses)
- Test interrupt flow (outline approval)
- Test debate loop (Validator reject → Story Miner loop → re-validate)

**Todo List:**
1. `tests/test_state.py` — test reducer functions, TypedDict validation
2. `tests/test_agents.py` — test setiap agent node dengan mock LLM
3. `tests/test_pipeline.py` — test full routing logic dengan mock state

---

## Dependencies (requirements.txt)

```
langgraph>=0.4.0
langchain>=0.3.0
langchain-core>=0.3.0
langchain-community>=0.3.0
langchain-chroma>=0.2.0
langchain-openai>=0.2.0
langchain-huggingface>=0.1.0
sentence-transformers>=3.0.0
chromadb>=0.6.0
tavily-python>=0.3.0
python-dotenv>=1.0.0
tiktoken>=0.7.0
```

---

## Environment Variables (.env)

```
# LLM Provider (pilih salah satu)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# LLM Model
LLM_MODEL=gpt-4o-mini   # ganti ke gpt-4o untuk production

# Web Search (optional — Web Researcher gracefully skips if missing)
TAVILY_API_KEY=tvly-...

# LangSmith Observability (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=arcwright
```

---

## Implementation Order

```
2.1 Scaffold  →  2.2 State  →  2.3 RAG Librarian  →  2.4 Story Miner
     →  2.5 Web Researcher  →  2.6 Deep Dive  →  2.7 Validator
     →  2.8 Outline Writer  →  2.9 Script Writer
     →  2.10 Story Director + Routing  →  2.11 Graph Pipeline
     →  2.12 HITL Node  →  2.13 CLI  →  2.14 Tests
```

**Build order principle:** Leaf agents dulu (no dependencies), lalu orchestrator, lalu graph.

---

## Context for Next Tasks

- ChromaDB path (absolute): `{PROJECT_ROOT}/forge/output/chroma_db/`
- Embedding model: `BAAI/bge-m3` (wajib konsisten dengan forge)
- Collection: `storytelling_books`
- Total chunks: 9,270 dari 26 buku
- `forge/arcwright/config.py` punya `CHROMA_DIR` dan `EMBEDDING_MODEL` yang bisa di-import
- Semua agent pakai `create_react_agent` dari `langgraph.prebuilt`
- Checkpointer: `SqliteSaver` dari `langgraph.checkpoint.sqlite` untuk dev, path: `sessions.db`

---

*Plan dibuat berdasarkan: docs/2026-07-10-arcwright-pla.md, docs/2026-07-10-arcwright-technical-architecture.md, docs/2026-07-10-arcwright-prd.md*
