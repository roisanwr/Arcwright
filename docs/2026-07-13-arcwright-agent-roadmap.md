# Arcwright: Multi-Agent System Implementation Roadmap
**Status:** RAG Pipeline (Phase 1) 100% Complete. Proceeding to Phase 2 (LangGraph Multi-Agent System).
**Deadline:** 31 July 2026

## 1. Project Scaffold & Shared State
**Objective:** Establish the foundational architecture and blackboard state.

*   **`agents/state.py`**: Define `ArcwrightState` (TypedDict/Pydantic) containing:
    *   `user_input`: Raw story input.
    *   `story_fragments`: Extracted themes, emotions, and details (from Story Miner).
    *   `rag_context`: Retrieved storytelling frameworks (from RAG Librarian).
    *   `web_context`: Real-time trends (from Web Researcher).
    *   `analysis`: Multi-perspective insights (from Deep Dive).
    *   `validation_score`: Outline quality score (from Validator).
    *   `debate_rounds`: Counter to prevent infinite loops (max 3).
    *   `outline_variants`: 2-3 structured outlines.
    *   `user_approved`: Boolean flag for Human-in-the-loop.
    *   `final_script`: The generated narrative.
    *   `platform_target`: YouTube, TikTok, Podcast, or Blog.

*   **`config/settings.py` & `config/prompts.yaml`**: Centralize API keys, Qdrant paths (`forge/output/qdrant_storage`), model selection (`ag/gemini-3.1-pro-low`), and all agent system prompts.

## 2. Agent Implementation Sequence (Prioritized)

### Priority 0: The Core Knowledge & Extraction Loop
1.  **RAG Librarian (`agents/rag_librarian.py`)**:
    *   **Role:** Connects to the existing Qdrant (9,270 chunks).
    *   **Function:** Uses MMR (top 5, fetch-k 20) via BGE-M3 to retrieve frameworks. Re-ranks using Layer 8 logic. Writes strictly to `rag_context`.
2.  **Story Miner (`agents/story_miner.py`)**:
    *   **Role:** The conversational interviewer.
    *   **Function:** Uses `rag_context` to ask smart questions (anchor, contrast, emotion). Extracts story fragments.

### Priority 1: Synthesis & Quality Control
3.  **Outline Writer (`agents/outline_writer.py`)**:
    *   **Role:** The story architect.
    *   **Function:** Synthesizes `story_fragments` and `rag_context` into 2-3 distinct outlines (Hook, Setup, Turning Point, Struggle, Resolution).
4.  **Validator (`agents/validator.py`)**:
    *   **Role:** The resonance checker.
    *   **Function:** Scores outlines on Relatability, Emotional Hook, Originality, Platform Fit, Trend Alignment (0-50 scale). Triggers debate if score < 35.

### Priority 2: Enrichment (Parallel Execution)
5.  **Deep Dive (`agents/deep_dive.py`)**:
    *   **Role:** Perspective explorer.
    *   **Function:** Analyzes surface, psychological, and universal themes.
6.  **Web Researcher (`agents/web_researcher.py`)**:
    *   **Role:** Real-time intelligence.
    *   **Function:** Uses Tavily to find competitor examples and audience trends.

### Priority 3: Finalization & Orchestration
7.  **Script Writer (`agents/script_writer.py`)**:
    *   **Role:** The narrative craftsman.
    *   **Function:** Expands the approved outline into a full script tailored to the `platform_target`. Includes a self-refine loop.
8.  **Story Director (`agents/story_director.py` & `graph/pipeline.py`)**:
    *   **Role:** The orchestrator.
    *   **Function:** Manages the LangGraph `StateGraph`. Defines conditional edges, arbitrates debates, and controls the `interrupt_before` node for human approval.

## 3. LangGraph Pipeline Flow
1.  **Mining Phase:** `Story Director` routes to `Story Miner` ↔ `RAG Librarian`.
2.  **Enrichment Phase:** `Deep Dive` & `Web Researcher` run in parallel (`Send()`).
3.  **Drafting Phase:** `Outline Writer` drafts variants.
4.  **Validation Phase:** `Validator` scores. If < 35, debate with `Story Miner` (max 3 rounds).
5.  **Approval Phase (Interrupt):** Halts graph. User reviews variants.
6.  **Scripting Phase:** `Script Writer` generates final content based on user choice.

## 5. Technical Implementation Details & Code Structures

### 5.1 Project Directory Setup
```bash
mkdir -p agents graph config tests logs
touch agents/__init__.py agents/state.py agents/story_director.py agents/story_miner.py agents/rag_librarian.py agents/web_researcher.py agents/validator.py agents/deep_dive.py agents/outline_writer.py agents/script_writer.py
touch graph/__init__.py graph/pipeline.py graph/edges.py
touch config/__init__.py config/settings.py config/prompts.yaml
```

### 5.2 State Schema (`agents/state.py`)
Using `TypedDict` and `Annotated` with `operator.add` for message appends.
```python
from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
from langchain_core.messages import BaseMessage

class ArcwrightState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_input: str
    platform_target: str
    phase: str
    
    # Knowledge & Extraction
    rag_context: str
    web_context: str
    story_fragments: Dict[str, Any]
    
    # Processing
    analysis: Dict[str, str]
    validation_score: int
    validation_feedback: str
    debate_rounds: int
    
    # Outputs
    outline_variants: List[Dict[str, str]]
    user_approved: bool
    final_script: str
```

### 5.3 Config & Settings (`config/settings.py`)
```python
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "forge" / "output" / "qdrant_storage"

# LLM Config (9Router via OpenAI wrapper)
LLM_API_URL = "http://0.0.0.0:20128/v1"
LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-default")
LLM_MODEL = "ag/gemini-3.1-pro-low"

# RAG Config
EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
COLLECTION_NAME = "storytelling_books"

# LangGraph limits
MAX_DEBATE_ROUNDS = 3
```

### 5.4 Graph Routing Logic (`graph/edges.py`)
```python
def route_after_validation(state: ArcwrightState) -> str:
    score = state.get("validation_score", 0)
    rounds = state.get("debate_rounds", 0)
    
    if score >= 35:
        return "outline_writer"
    elif rounds >= 3:
        # Max rounds reached, force proceed or escalate to Director
        return "story_director_arbitration" 
    else:
        return "story_miner" # Revise
```

### 5.5 Shared LLM Utility (`utils/llm.py`)
Must enforce `stream=False` for 9Router compatibility.
```python
from langchain_openai import ChatOpenAI
from config import settings

def get_llm(temperature=0.7):
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_URL,
        temperature=temperature,
        model_kwargs={"stream": False} # CRITICAL for 9Router
    )
```

## 6. Development Milestones
1. **Milestone 1 (T+2 Days):** State schema, Utils, and `RAG Librarian` successfully querying Qdrant within a test graph.
2. **Milestone 2 (T+5 Days):** Core loop working: `Story Miner` ↔ `RAG Librarian` ↔ `Validator` (Debate loop functioning).
3. **Milestone 3 (T+8 Days):** Parallel nodes working (`Deep Dive`, `Web Researcher`) and merging cleanly back into state.
4. **Milestone 4 (T+10 Days):** Full pipeline generating scripts (`Outline Writer`, Human-Interrupt, `Script Writer`).
5. **Milestone 5 (T+14 Days):** Production hardening (retries, LangSmith, testing).