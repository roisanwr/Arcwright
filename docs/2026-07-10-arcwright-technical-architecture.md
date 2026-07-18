---
id: "202607101530"
title: "Arcwright Technical Architecture — LangGraph + RAG Multi-Agent System"
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
  - "[[2026-07-10-arcwright-prd]]"
  - "[[2026-07-08-storytelling-ai-agent-roles]]"
---

# ⚙️ Arcwright Technical Architecture

> **System:** Storytelling AI Multi-Agent on LangGraph + Qdrant RAG
> **Version:** 1.0
> **Stack:** Python 3.12, LangGraph, Qdrant, BGE-M3
> **Connects to:** [[2026-07-10-arcwright-pla]], [[2026-07-10-arcwright-prd]], [[Arcwright forge/]]

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE (CLI)                      │
│                     main.py — stdin/stdout loop                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LANGGRAPH PIPELINE                           │
│                     graph/pipeline.py                            │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   STORY DIRECTOR NODE                      │  │
│  │            (Supervisor — orchestrator logic)               │  │
│  │  Routes: classify_intent → decide_next → goto(agent)      │  │
│  └────────────┬────────────┬──────────────┬──────────────────┘  │
│               │            │              │                      │
│        ┌──────▼──┐  ┌─────▼─────┐  ┌─────▼──────┐              │
│        │ STORY   │  │  VALIDATOR│  │ DEEP DIVE  │              │
│        │ MINER   │  │  NODE     │  │ NODE       │              │
│        └─────────┘  └───────────┘  └────────────┘              │
│               │            │              │                      │
│        ┌──────▼──┐  ┌─────▼─────┐  ┌─────▼──────┐              │
│        │ RAG     │  │ OUTLINE   │  │ WEB        │              │
│        │LIBRARIAN│  │ WRITER    │  │ RESEARCHER │              │
│        └─────────┘  └───────────┘  └────────────┘              │
│               │            │              │                      │
│        ┌──────▼────────────▼──────────────▼──────┐              │
│        │           SCRIPT WRITER NODE             │              │
│        └────────────────┬─────────────────────────┘              │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ARCRIGHT FORGE (RAG)                        │
│  forge/output/qdrant_storage/  ← Qdrant PersistentClient           │
│  forge/data/extracted/    ← Extracted markdown                   │
│  forge/arcwright/         ← Python package (extract, chunk,      │
│                              embed, pipeline)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. LangGraph Pipeline Design

### 2.1 StateGraph Definition

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, Send, interrupt

# See PLA.md for full ArcwrightState definition
# Key fields:
# - current_phase: mining → enriching → validating → outlining → scripting
# - messages: chat history
# - story_fragments: accumulated fragments
# - agent_notes: inter-agent communication board
# - validation_result: validator output
# - story_outline: outline writer output
# - output_script: final script

def create_arcwright_graph() -> StateGraph:
    """Build the full multi-agent pipeline."""
    builder = StateGraph(ArwrightState)
    
    # Register all agent nodes
    builder.add_node("story_director", story_director_node)
    builder.add_node("story_miner", story_miner_node)
    builder.add_node("rag_librarian", rag_librarian_node)
    builder.add_node("web_researcher", web_researcher_node)
    builder.add_node("deep_dive", deep_dive_node)
    builder.add_node("validator", validator_node)
    builder.add_node("outline_writer", outline_writer_node)
    builder.add_node("script_writer", script_writer_node)
    builder.add_node("user_approval", user_approval_node)
    
    # Entry point
    builder.add_edge(START, "story_director")
    
    # Core flow edges
    builder.add_edge("story_miner", "story_director")
    builder.add_edge("rag_librarian", "story_director")
    builder.add_edge("web_researcher", "story_director")
    builder.add_edge("deep_dive", "story_director")
    builder.add_edge("outline_writer", "story_director")
    builder.add_edge("user_approval", "story_director")
    builder.add_edge("script_writer", END)
    
    # Supervisor decides next agent based on state
    builder.add_conditional_edges(
        "story_director",
        story_director_routing,  # Returns name of next node
        {
            "story_miner": "story_miner",
            "rag_librarian": "rag_librarian",
            "web_researcher": "web_researcher",
            "deep_dive": "deep_dive",
            "validator": "validator",
            "outline_writer": "outline_writer",
            "user_approval": "user_approval",
            "script_writer": "script_writer",
            END: END,
        }
    )
    
    # Debate loop: validator can route back to story_miner
    builder.add_conditional_edges(
        "validator",
        validator_debate_routing,  # Returns "outline_writer" or "story_miner" or "story_director"
        {
            "outline_writer": "outline_writer",
            "story_miner": "story_miner",
            "story_director": "story_director",
        }
    )
    
    return builder.compile(
        checkpointer=MemorySaver(),  # SQLite for persistence
        interrupt_before=["user_approval"],  # Pause for user input
    )
```

### 2.2 Story Director Routing Logic

```python
def story_director_routing(state: ArcwrightState) -> str:
    """
    Story Director decides which agent to call next.
    Uses state machine transitions based on current_phase.
    """
    phase = state.get("current_phase", "mining")
    
    # Phase: Mining — user hasn't shared enough yet
    if phase == "mining":
        if len(state.get("story_fragments", [])) < 2:
            # Need more material
            if state.get("rag_context"):
                return "story_miner"  # Already have RAG context
            else:
                return "rag_librarian"  # Get RAG context first
        else:
            return "story_director"  # Move to enriching phase
    
    # Phase: Enriching — we have fragments, deepen them
    elif phase == "enriching":
        if not state.get("deep_dive_analysis"):
            # Run deep dive + web research in parallel
            return "deep_dive"  # Will also trigger web_researcher via Send()
        elif not state.get("validation_result"):
            return "validator"
        else:
            return "outline_writer"
    
    # Phase: Validating — check outline quality
    elif phase == "validating":
        if state.get("validation_result", {}).get("passed"):
            return "user_approval"  # Present to user
        else:
            return "story_miner"  # Gather more material
    
    # Phase: Outlining — produce the outline
    elif phase == "outlining":
        if state.get("story_outline"):
            return "validator"  # Validate before showing user
        else:
            return "outline_writer"
    
    # Phase: Scripting — produce final script
    elif phase == "scripting":
        return "script_writer"
    
    # Phase: Complete
    elif phase == "complete":
        return END
    
    # Fallback
    return "story_miner"
```

### 2.3 Debate Routing (Validator ↔ Story Miner)

```python
def validator_debate_routing(state: ArcwrightState) -> str:
    """
    After validator scores an outline:
    - PASS (≥35/50): send back to Story Director → move to user approval
    - REVISE (25-34): loop to Story Miner with feedback
      BUT max 3 rounds → escalate to Story Director
    - REJECT (<25): loop to Story Miner for new material
      BUT max 3 rounds → escalate to Story Director
    """
    result = state.get("validation_result", {})
    score = result.get("score", 0)
    rounds = state.get("debate_rounds", 0)
    
    if score >= 35:
        # PASS - move forward
        return "story_director"
    
    if rounds >= 3:
        # Max rounds reached - Story Director arbitrates
        return "story_director"
    
    if 25 <= score < 35:
        # REVISE - loop back for refinement
        return "story_miner"
    
    # REJECT (<25) - need new material
    return "story_miner"
```

---

## 3. Agent Implementation Details

### 3.1 RAG Librarian Agent (Connects to Arcwright Forge)

```python
from langgraph.prebuilt import create_react_agent
from langchain_chroma import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.tools.retriever import create_retriever_tool
import qdrant

# Connect to Arcwright forge Qdrant
chroma_client = qdrant.PersistentClient(
    path="/home/rois/Arcwright/forge/output/qdrant_storage"
)

# Use BGE-M3 (same model as forge)
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

vector_store = Qdrant(
    client=chroma_client,
    embedding_function=embeddings,
    collection_name="storytelling_books"  # Or multi-collection
)

retriever = vector_store.as_retriever(
    search_type="mmr",  # Maximum Marginal Relevance for diversity
    search_kwargs={"k": 5, "fetch_k": 20}
)

rag_tool = create_retriever_tool(
    retriever,
    name="search_storytelling_knowledge",
    description=(
        "Search the storytelling knowledge base for frameworks, techniques, "
        "and narrative structures. Use this to find: questioning techniques, "
        "story frameworks (Hero's Journey, Save the Cat), audience psychology, "
        "and narrative writing tips."
    )
)

rag_librarian_agent = create_react_agent(
    model=llm,
    tools=[rag_tool],  # ONLY this tool — zero bleed to other domains
    state_modifier="""You are the RAG Librarian Agent.
Your ONLY job is to retrieve relevant storytelling knowledge from the library.

When queried:
1. Search the vector database for the most relevant techniques
2. Return the framework/technique with source attribution (book title + section)
3. Explain WHY it's relevant to the current context
4. Do NOT suggest stories or converse with the user — only supply knowledge

Available techniques include: Hero's Journey, Save the Cat beat sheet,
Story Spine, Pixar storytelling rules, narrative psychology, 
audience resonance frameworks, questioning techniques for story mining.
"""
)
```

### 3.2 Story Miner Agent

```python
# Story Miner has NO external tools — pure conversational agent
story_miner_agent = create_react_agent(
    model=llm,
    tools=[],  # Pure conversation — no external access
    state_modifier="""You are the Story Mining Agent — an empathetic interviewer.

Your job is to help users discover stories from their everyday life.

Rules:
1. Ask ONE question at a time (never multiple questions)
2. Start broad, then drill into specific sensory details
3. Listen for emotional moments and dig deeper
4. Extract: theme, emotion, character, conflict, specific moment
5. After user answers, extract story fragments and store them
6. Do NOT suggest stories — draw them out of the user
7. Keep tone warm and conversational

When you have 2-3 solid story fragments, signal completion.
If user is stuck, use contrasting questions ("what was different today?").
"""
)
```

### 3.3 Validator Agent

```python
validator_agent = create_react_agent(
    model=llm,
    tools=[audience_trend_tool],  # Can check audience data
    state_modifier="""You are the Story Validator — a quality gate for narratives.

You evaluate story outlines on 5 criteria (each 0-10):
1. RELATABILITY: Will many people connect with this story?
2. EMOTIONAL HOOK: Does it evoke genuine emotion?
3. ORIGINALITY: Is the perspective fresh or generic?
4. PLATFORM FIT: Does it match the target platform format?
5. TREND ALIGNMENT: Is it relevant to current audience interests?

Scoring:
- ≥35/50: PASS — proceed to outline presentation
- 25-34: REVISE — provide specific feedback on weak areas
- <25: REJECT — explanation of why it won't resonate

When REVISE or REJECT, engage in debate with Story Mining Agent:
- Round 1: Explain your critique with specific reasoning
- Round 2: Respond to Story Miner's counterpoints
- Round 3: Final assessment (or escalate to Story Director)

Be constructive, not dismissive. Your goal is to improve the story,
not kill it.
"""
)
```

---

## 4. Agent Communication Protocol

### 4.1 Shared State (Blackboard Pattern)

```
All agents communicate via ArcwrightState — no direct agent-to-agent calls.

STORY MINER ──writes──→ story_fragments[]
                     rag_librarian ←──reads── RAG LIBRARIAN
                     
RAG LIBRARIAN ──writes──→ rag_context[]
                     outline_writer ←──reads── OUTLINE WRITER

DEEP DIVE ──writes──→ deep_dive_analysis{}
                     validator ←──reads── VALIDATOR

AGENT COMMUNICATION BOARD:
    agent_notes: [
        {"agent": "story_miner", "type": "flag", "content": "User got emotional about..."},
        {"agent": "validator", "type": "critique", "content": "This angle is too generic..."},
    ]
```

### 4.2 Execution Guarantees

- **No agent calls another agent directly** — all routing via Story Director
- **Sequential execution** (LangGraph default) — simplifies debugging
- **Parallel via `Send()`** — Deep Dive + Web Researcher run simultaneously
- **Thread safety** — single-threaded graph execution prevents race conditions

---

## 5. RAG Integration Architecture

### 5.1 Arcwright Forge → LangGraph Connection

```
                        ┌─────────────────────────┐
                        │     LANGGRAPH AGENTS      │
                        │                           │
                        │  RAG Librarian Agent      │
                        │    (create_react_agent)   │
                        │         │                 │
                        │     [rag_tool]            │
                        │         │                 │
                        │  create_retriever_tool()  │
                        └─────────┬─────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────┐
│                     ARCRIGHT FORGE                            │
│                                                               │
│  forge/output/qdrant_storage/                                      │
│  ├── chroma.sqlite3           ← Qdrant persistence          │
│  └── ...                     ← Embedding index files          │
│                                                               │
│  Qdrant(                                                      │
│      client=PersistentClient(path="forge/output/qdrant_storage"),   │
│      embedding_function=BGE-M3,                               │
│      collection_name="storytelling_books"                     │
│  )                                                            │
│                                                               │
│  Collections (per-book or unified):                            │
│  ├── story_books_main  ← All 29 books merged                  │
│  └── story_books_*     ← Individual book collections          │
│                                                               │
│  Each document:                                                │
│  { id, text, title, section, source, char_count }             │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Data Flow: RAG Query

```
1. Story Director detects: "need storytelling framework"
2. → RAG Librarian receives context with story fragments
3. → Constructs query: "What Hero's Journey variation fits a story about [theme]?"
4. → Calls retriever/search_storytelling_knowledge("...")
5. → Qdrant returns top-5 chunks with metadata
6. → RAG Librarian formats: "Based on [Book] > [Section]: [technique]"
7. → Writes to rag_context[] in shared state
8. → Story Director routes result to Outline Writer
```

---

## 6. Error Handling Strategy

| Error Type | Detection | Response |
|-----------|-----------|----------|
| **Agent timeout** | >30s no response | Retry up to 3x; if fail, log + skip agent |
| **Empty RAG results** | 0 chunks returned | Fall back to general LLM knowledge |
| **Web search failure** | HTTP error | Cache last results; use stale data |
| **Validation deadlock** | 3 debate rounds | Story Director picks best option |
| **User disconnection** | No input >5min | Save state; resume later |
| **State corruption** | Schema mismatch | Revert to last checkpoint |

```python
# Graceful degradation
def safe_agent_call(agent_fn, state, max_retries=3):
    for attempt in range(max_retries):
        try:
            return agent_fn(state)
        except TimeoutError:
            state["error_count"] += 1
            log_warning(f"Agent timeout, attempt {attempt+1}")
            continue
        except Exception as e:
            state["error_count"] += 1
            log_error(f"Agent failed: {e}")
            if attempt == max_retries - 1:
                return {"error": str(e)}
    return {"error": "max retries exceeded"}
```

---

## 7. Session Persistence

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# SQLite checkpointing — auto-persists every step
checkpointer = SqliteSaver.from_conn_string(
    "sqlite:///home/rois/Arcwright/sessions.db"
)

# Each user gets a unique thread_id
# Session can be resumed by loading from checkpoint
config = {
    "configurable": {
        "thread_id": session_id,  # UUID per session
        "user_id": user_id,       # Cross-session identity
    }
}

# Resume interrupted session
thread_history = list(checkpointer.get("thread_id"))
last_state = thread_history[-1] if thread_history else None
```

---

## 8. LangSmith Observability

```python
# Enable tracing
from langsmith import Client
import os

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "arcwright"

# Every graph step is traced:
# - Agent calls (token count, latency)
# - Edge traversals (routing decisions)
# - State changes (what each agent wrote)
# - Interrupts (user interaction points)

# Debugging: LangSmith dashboard shows
# - Per-agent latency breakdown
# - Token consumption per step
# - State diff at each transition
# - Error locations with full context
```

---

## 9. Development Setup

### 9.1 Prerequisites
```bash
# Already installed
cd ~/Arcwright
source venv/bin/activate

# Additional dependencies for LangGraph
pip install langgraph langgraph-supervisor langchain langchain-community \
            langchain-chroma sentence-transformers qdrant tiktoken
```

### 9.2 Directory Structure (Final)
```
~/Arcwright/
├── agents/                  # NEW: Agent definitions
│   ├── __init__.py
│   ├── state.py             # ArcwrightState TypedDict
│   ├── story_director.py    # Supervisor routing logic
│   ├── story_miner.py       # Conversational miner
│   ├── rag_librarian.py     # RAG retriever agent
│   ├── web_researcher.py    # Web search agent
│   ├── validator.py         # Quality validator
│   ├── deep_dive.py         # Perspective analyst
│   ├── outline_writer.py    # Story structure builder
│   └── script_writer.py     # Narrative writer
├── graph/                   # NEW: Graph definition
│   ├── __init__.py
│   ├── pipeline.py          # StateGraph build + compile
│   └── edges.py             # Conditional routing functions
├── config/                  # NEW: Configuration
│   ├── settings.py          # Model names, paths, API keys
│   └── prompts.yaml         # Agent system prompts
├── forge/                   # EXISTING: RAG pipeline
│   └── output/qdrant_storage/    # Vector store
├── main.py                  # NEW: CLI entry point
├── tests/                   # NEW: Test suite
│   ├── test_rag.py          # RAG query tests
│   ├── test_agents.py       # Individual agent tests
│   └── test_pipeline.py     # End-to-end pipeline test
├── requirements.txt         # Updated deps
└── README.md                # Updated docs
```

### 9.3 Running the System
```bash
# Interactive CLI session
cd ~/Arcwright && source venv/bin/activate
python main.py

# You'll see:
# ==========================================
#  🎭 Arcwright — Storytelling AI Assistant
# ==========================================
# Hi! I'm Yui, your Storytelling Coach. ✨
# 
# Tell me a bit about yourself...
# Do you have a story in mind, or want help finding one?
# 
# > I don't know what to talk about
# ...
```

---

## 10. Testing Strategy

| Test Type | What | Tool | When |
|-----------|------|------|------|
| **Unit** | Individual agent nodes | pytest | Per agent |
| **Integration** | Agent chains (Miner→Validator→Outline) | pytest | Per edge |
| **RAG** | Query relevance, recall@k | pytest + manual | Per book added |
| **Pipeline** | Full end-to-end (input→output) | pytest | Per phase |
| **Debate** | Validator↔Miner loop, max rounds | pytest | Post debate logic |
| **Latency** | Per-agent timing | LangSmith | Each run |
| **User** | Session completion, approval rate | Session logs | Weekly |

---

*Generated by Hermes (Yui) on 2026-07-10 — Full technical specification for Arcwright v1.0*
