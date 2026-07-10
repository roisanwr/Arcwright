# Agentic AI Frameworks: State-of-the-Art Research
## For Conversational Storytelling AI with 6–8 Specialized Agents
*Research Date: July 2026*

---

## 1. LangGraph (LangChain)

### Core Architecture
LangGraph models agent workflows as **directed graphs** (`StateGraph`) where nodes are functions/agents and edges define execution flow. Every node reads from and writes to a **shared typed state object** — the canonical communication bus.

### Key Concepts

**StateGraph & Typed State**
- State is a Python `TypedDict` or Pydantic model shared across all nodes.
- Each node receives the current state and returns a partial update; a **reducer** function merges it.
- Default reducer = overwrite; custom reducers (e.g., `operator.add` for message lists) enable append semantics.
- Multiple schemas: `InputState` / `OutputState` / private `PrivateState` — different views of state per node.

**Conditional Edges**
- `add_conditional_edges(source, routing_fn, mapping)` — routing function inspects state and returns the name of the next node (or `END`).
- Enables branching, looping, retries, and dynamic dispatch.
- `Send()` API allows fan-out: spawning multiple parallel branches with different state slices.

**Subgraphs (Multi-Agent)**
- A subgraph is a compiled `StateGraph` invoked as a node in a parent graph — each subgraph has its own state schema.
- Patterns supported: **supervisor** (one orchestrator node routes to specialist agents), **hierarchical** (nested supervisors), **swarm/handoff** (agents pass `Command` objects to transfer control), **network** (agents can call each other freely).
- `Command` object: a node returns `Command(goto="other_node", update={...})` for conditional routing from within a node.

**Persistence & Memory**
- **Checkpointers**: SQLite, PostgreSQL, Redis, custom. Every graph step auto-checkpointed.
- **Thread**: a unique ID (`thread_id`) for a conversation session. All checkpoints stored per-thread = persistent memory across sessions by default.
- **Stores** (cross-thread): a separate key-value store for long-term memory shared across threads (semantic/episodic/profile memory).
- Memory types: short-term (in-state), long-term (via Store), semantic (vector embeddings in Store), episodic (stored past runs), procedural (system prompt updates from Store).
- **Time Travel**: replay any past checkpoint, inspect state at any node.
- **Human-in-the-loop**: `interrupt()` call pauses graph mid-execution for human approval.

**Agent Communication**
- All agents share one typed state — no message passing, just state mutations.
- `messages` list with `MessagesState` is the idiomatic pattern (similar to chat history).
- Agents can also write to any state field → coordination via structured state fields.

**Tool Assignment**
- Each agent node is typically a `create_react_agent(llm, tools=[...])` subgraph or a custom node with its own bound tools.
- Tools are fully scoped to a specific agent — different agents can have disjoint or overlapping tool sets.

**Debate/Validation**
- No built-in debate mechanism.
- Achievable via looping edges: Agent A produces draft → Agent B critiques → conditional edge loops back if critique fails → Agent A revises.
- Custom with `Command` or conditional edges for multi-round validation patterns.

**RAG Integration**
- Native via LangChain's RAG primitives: `VectorStoreRetriever` wraps any vector DB (Chroma, Pinecone, Weaviate, Qdrant, MongoDB, etc.).
- A retriever can be a tool assigned to specific agents.
- LangChain has 50+ vector store integrations.

**Web Search**
- Tavily (first-party), SerperAPI, DuckDuckGo, Brave, Bing — all available as LangChain tools.
- Can be scoped to specific agent nodes.

**Observability**
- LangSmith: trace every node, state snapshot, edge traversal, token usage.
- LangGraph Studio: visual drag-and-drop graph editor + live debugging.

**Learning Curve**: High. Requires understanding graphs, reducers, state schemas, checkpointers, subgraphs. Powerful but verbose.

**GitHub**: ~46k stars. Production-grade, widely adopted.

---

## 2. CrewAI

### Core Architecture
CrewAI is a **role-based multi-agent framework** built on the metaphor of a "crew" of specialized agents working on "tasks". Conceptually simpler than LangGraph — you define agents with roles/goals, assign tasks to agents, and the crew executes them.

### Key Concepts

**Agents**
- Defined by: `role`, `goal`, `backstory`, `llm`, `tools`, `memory`, `verbose`, `max_iter`, `allow_delegation`.
- Each agent has its own LLM (can differ per agent), tool list, and memory settings.
- **Delegation**: an agent can delegate sub-tasks to other agents via `allow_delegation=True` — the agent decides dynamically which crew member to delegate to.

**Tasks**
- Tasks have: `description`, `expected_output`, `agent`, `tools` (can override agent tools), `context` (output of prior tasks), `output_pydantic` (structured output), `callback`.
- Task output becomes context for subsequent tasks — pipeline-style chaining.
- `async_execution=True` for parallel tasks.

**Processes (Hierarchy)**
- `Process.sequential` (default): tasks run in order, output of task N is context for task N+1.
- `Process.hierarchical`: a **manager LLM** acts as orchestrator. It plans, delegates tasks to agents, and reviews outputs. Manager does NOT need to be pre-configured — a dedicated `manager_llm` is specified at crew level.
- Manager agent in hierarchical mode: creates subtasks, assigns them to the best crew member, reviews their outputs, requests revisions if needed — autonomous project management.
- Custom manager agent can be specified for full control.

**Flows**
- `@start`, `@listen`, `@router` decorators for event-driven orchestration.
- Can chain multiple Crews within a Flow, passing data between them.
- Enables complex conditional branching and multi-crew pipelines.

**Memory System (Built-in)**
- `short_term_memory`: in-run context (RAG-based, uses embeddings).
- `long_term_memory`: persisted to SQLite across runs — agents remember past task outcomes.
- `entity_memory`: tracks entities mentioned (characters, places, objects) — powered by embeddings.
- `user_memory`: user-specific memory using `mem0` library.
- `knowledge`: external knowledge sources (PDFs, URLs, text, JSON, CSVs) embedded and queried at task time — acts as built-in RAG.
- External memory (Zep, Mem0) also supported.

**Tool Assignment**
- Tools assigned at agent level OR task level (task tools override agent tools).
- Built-in tools: WebsiteSearchTool, SerperDevTool (web search), FileReadTool, DirectoryReadTool, PDFSearchTool, CodeInterpreterTool, BrowserbaseTool, etc.
- `@tool` decorator for custom tools.
- **MCP support**: connect any MCP server as a tool source.

**RAG Integration**
- `CrewAI Knowledge` subsystem: source documents (text, PDF, CSV, JSON, URL) automatically chunked, embedded, and stored in a vector DB (default: Chroma).
- Agents query the knowledge base automatically when relevant.
- Custom vector store backends supported (e.g., Pinecone via LangChain integration).

**Web Search**
- `SerperDevTool`, `EXASearchTool`, `BraveSearchTool`, `TavilySearchTool`, `FirecrawlSearchTool` — all built-in.
- Assign per-agent.

**Debate/Voting**
- No native debate mechanism.
- Hierarchical process with manager review approximates validation.
- Custom implementation possible via task callbacks and delegation patterns.

**Observability**
- Built-in event listeners (`@before_task_start`, `@after_task_complete`, etc.).
- CrewAI Enterprise dashboard (SaaS).
- OpenTelemetry-compatible tracing.

**Learning Curve**: Low–Medium. Intuitive role/task paradigm. Quick to prototype.

**GitHub**: ~55k stars (most popular framework in this comparison).

---

## 3. Microsoft AutoGen (v0.4 / v0.7.5 stable)

### Core Architecture
AutoGen is a **conversation-pattern-based** multi-agent framework. In v0.4+, the architecture is split into two layers:
- **`autogen-core`**: low-level async actor model with explicit message passing — agents are actors that send/receive typed messages.
- **`autogen-agentchat`**: high-level opinionated API with `Agent`, `Team`, built-in group chat patterns.

### AgentChat Teams (Group Chat Patterns)

**RoundRobinGroupChat**
- Agents take turns in fixed round-robin order.
- All agents share the same message context (broadcast model).
- Good for structured workflows where each agent has a defined step.

**SelectorGroupChat** (most powerful for storytelling)
- An LLM-based selector reads the shared context and selects the next speaker.
- Fully customizable: `selector_prompt`, `allow_repeated_speaker`, `candidate_func` (narrow candidates), `selector_func` (override selection entirely).
- Enables dynamic, context-aware agent ordering — the selector sees all agent descriptions and conversation history.
- This is AutoGen's closest native analog to a "debate": multiple agents contribute in an intelligent order.

**Swarm**
- Agents use `HandoffMessage` to explicitly hand off control to named agents.
- Local decisions: each agent decides who to hand off to next (no central orchestrator).
- All agents share message context.
- Good for sequential task handoff pipelines.

**MagenticOneGroupChat**
- Orchestrator + specialist agents pattern.
- Orchestrator (LLM-powered) creates and updates a task ledger, assigns steps to agents, reviews completions.
- Built-in: FileSurfer, WebSurfer, Coder, ComputerTerminal agents.
- Most autonomous team type — handles complex multi-step tasks.

**GraphFlow** (newest)
- Directed graph of agents — explicitly define which agents can follow which.
- Mix sequential, parallel (parallel edges), conditional transitions.
- Closest to LangGraph in concept but simpler API.

**Human-in-the-Loop**
- `UserProxyAgent` or custom agent to inject human messages.
- Interrupt/resume conversation at any point.

**Memory and RAG**
- `MemoryStore` interface with default `ListMemory` (conversation history).
- `ChromaDBMemory` built-in for vector RAG — query memory on every agent call.
- Custom memory: implement `Memory` protocol.
- AutoGen v0.4 has explicit `Memory and RAG` guide with ChromaDB and custom backends.
- State management: `save_state()` / `load_state()` on any team — serialized to JSON for persistence across sessions.

**Agent Communication**
- Broadcast model: all agents in a team see all messages.
- Structured typed messages (`TextMessage`, `ToolCallMessage`, `HandoffMessage`, `StopMessage`, etc.).
- `autogen-core` supports point-to-point, broadcast, and request-response patterns with explicit message routing.

**Debate Mechanism**
- No built-in native debate.
- SelectorGroupChat enables sequential critique by using a selector that picks "critic" agents after "creator" agents.
- Can implement: Author → Critic loop using custom termination condition or selector function.
- Best for structured debate: define Creator, Critic, Judge agents + custom `selector_func` that enforces A→B→A→B→Judge pattern.

**Tool Assignment**
- Tools assigned per-agent at construction: `AssistantAgent(tools=[tool1, tool2])`.
- Different agents have different tool sets.

**Web Search**
- Via tool: use Tavily, Bing, Brave etc. as a Python tool function registered on specific agents.
- AutoGen Extensions: `autogen-ext` has built-in web browsing via `WebSurfer` (Playwright-based).

**Observability**
- OpenTelemetry tracing via `autogen-ext`.
- File/console logging with structured events.
- AutoGen Studio: web-based GUI to build and run teams visually.

**Structured Output**
- Any agent can be configured with a Pydantic response model for type-safe output.

**Learning Curve**: Medium. AgentChat API is clean but the two-layer architecture (core vs. agentchat) can confuse. More boilerplate than CrewAI but more explicit control.

**GitHub**: ~43k stars.

---

## 4. AgentScope (Alibaba / ModelScope)

### Core Architecture
AgentScope (v0.1.x → v2.0) is a **message-passing multi-agent framework** built for distributed/multi-process scenarios. The paradigm: agents communicate by **passing `Msg` objects** — typed messages with role, content, name, and optional metadata.

### Key Concepts

**Agents**
- All agents inherit from `AgentBase`. Built-in types: `DialogAgent`, `UserAgent`, `ReActAgent`, `DictDialogAgent`, `GroupChat`.
- `AgentBase.__call__(msg)` → `Msg`: agents are callable objects.
- Each agent maintains its own memory independently.

**Pipeline / Orchestration**
- `msghub()` context manager: a shared message hub where agents subscribe and broadcast.
- `pipeline` module: `sequential`, `forking`, `ifelse`, `whileloop`, `switchcase` combinators.
- Agents in a `msghub` context see all published messages.
- Operator composition: agents can be chained with `|` (pipe) operator.

**Distributed / Actor Model**
- Agents can run as distributed actors across multiple processes/machines.
- `to_dist()` converts a local agent to a distributed RPC-based actor.
- Designed for large-scale multi-agent simulations (e.g., many simultaneous agents).

**Memory**
- Per-agent `MemoryBase` with `TemporaryMemory` (in-memory buffer) and `PersistentMemory` (file-based JSON).
- `memory.add()`, `memory.get_memory()`, `memory.delete_memory()`, `memory.load_memory()`.
- RAG integration via `AgentScope RAG` module — supports Faiss, Milvus, LlamaIndex, MongoDB (recently added) for vector retrieval.
- Cross-session persistence: `PersistentMemory` writes to disk; can be reloaded on next run.

**Communication Patterns**
- Sequential: agent A outputs to agent B inputs.
- Forking: same message sent to multiple agents simultaneously.
- If/else and while-loop: dynamic branching via pipeline operators.
- `msghub`: publish/subscribe for group scenarios.
- No built-in supervisor/manager agent (must be custom-coded).

**Debate / Voting**
- AgentScope explicitly supports **multi-agent debate** patterns.
- Example: `GroupChat` with a moderator. Agents exchange positions; moderator summarizes/decides.
- Built-in `DictDialogAgent` can enforce structured outputs for voting/debate scenarios.
- Research-grade usage: used in simulations of debates, elections, social interactions.

**RAG Integration**
- `AgentScope RAG` module: supports LlamaIndex as retrieval backbone.
- Vector stores: Faiss, Milvus, MongoDB (new), Chroma.
- `RAGKnowledgeBase` class: load documents → embed → retrieve → inject into agent context.
- Also supports HuggingFace embeddings.

**Web Search**
- Via tool: `bing_search`, `google_search` service functions.
- `@service_func` decorator wraps any Python function as an agent tool.
- No dedicated built-in tool manager, but flexible tool registration.

**Structured Output**
- `DictDialogAgent`: enforces JSON/dict output from agents via prompt engineering.
- Post-parsers for structured extraction.

**Observability**
- `AgentScope Studio`: web dashboard for monitoring agent runs, message flows.
- `logger.chat()` for conversation logging.
- Distributed tracing for multi-process scenarios.

**Learning Curve**: Medium–High. The message-passing paradigm is powerful but different from mainstream frameworks. Documentation lags behind LangGraph/CrewAI.

**GitHub (agentscope-ai)**: ~27.6k stars. More research-oriented than production-focused.

---

## 5. Comprehensive Comparison Table

| Feature | **LangGraph** | **CrewAI** | **AutoGen** | **AgentScope** |
|---|---|---|---|---|
| **Paradigm** | Graph-based state machine | Role-task crew | Conversation patterns | Message-passing actors |
| **Version (Jul 2026)** | v0.4+ (stable) | v1.15.2 | v0.7.5 | v0.1.x → v2.0 |
| **GitHub Stars** | ~46k | ~55k | ~43k | ~27.6k |
| **Hierarchy (Boss Agent)** | ⭐⭐⭐⭐⭐ Native supervisor pattern; nested subgraphs; explicit `Command` routing | ⭐⭐⭐⭐ Native `Process.hierarchical` with manager LLM | ⭐⭐⭐⭐ `MagenticOneGroupChat` orchestrator; `SelectorGroupChat` | ⭐⭐ Manual via pipeline; no built-in supervisor |
| **Peer Agent Communication** | ⭐⭐⭐ Shared state (indirect); `Command` for explicit handoff | ⭐⭐⭐ Task context passing; delegation | ⭐⭐⭐⭐⭐ Native broadcast; all agents see all messages | ⭐⭐⭐⭐⭐ `msghub` publish/subscribe; explicit message routing |
| **Debate / Validation** | ⭐⭐⭐ Custom via looping edges + conditional | ⭐⭐ Manager review in hierarchical mode | ⭐⭐⭐⭐ `SelectorGroupChat` with Critic agents; custom `selector_func` | ⭐⭐⭐⭐ Native GroupChat debate patterns; used in research |
| **Built-in Voting** | ❌ None built-in | ❌ None built-in | ❌ None built-in | ⭐⭐⭐ Research-grade voting patterns via `DictDialogAgent` |
| **RAG Integration** | ⭐⭐⭐⭐⭐ 50+ vector store integrations via LangChain; retriever-as-tool per agent | ⭐⭐⭐⭐ Native `Knowledge` subsystem; Chroma default; custom backends | ⭐⭐⭐⭐ `ChromaDBMemory` built-in; custom `Memory` protocol | ⭐⭐⭐ RAG module; Faiss, Milvus, MongoDB, LlamaIndex |
| **Web Search Tools** | ⭐⭐⭐⭐⭐ Tavily, Serper, Brave, Bing, DuckDuckGo (LangChain tools) | ⭐⭐⭐⭐⭐ SerperDev, EXA, Brave, Tavily, Firecrawl (built-in tools) | ⭐⭐⭐⭐ WebSurfer (Playwright); Tavily via tool | ⭐⭐⭐ Bing/Google via service functions |
| **Memory Across Sessions** | ⭐⭐⭐⭐⭐ First-class: checkpointers (SQLite/Postgres), Stores, thread IDs | ⭐⭐⭐⭐⭐ Built-in long-term (SQLite), entity, user memory (mem0); Knowledge base | ⭐⭐⭐ `save_state()`/`load_state()`; ChromaDB memory; custom Memory protocol | ⭐⭐⭐ `PersistentMemory` (disk); per-agent; no shared cross-session store |
| **Structured Output** | ⭐⭐⭐⭐⭐ Pydantic state schema; per-node output validation | ⭐⭐⭐⭐⭐ `output_pydantic` per task; JSON mode | ⭐⭐⭐⭐ Pydantic response model per agent | ⭐⭐⭐ `DictDialogAgent`; custom parsers |
| **Tool Scoping per Agent** | ⭐⭐⭐⭐⭐ Each agent node has its own tool list | ⭐⭐⭐⭐⭐ Agent-level AND task-level tool assignment | ⭐⭐⭐⭐⭐ Per-agent tool registration | ⭐⭐⭐ Service functions scoped per agent |
| **Interactive Conversation (Human-in-Loop)** | ⭐⭐⭐⭐⭐ `interrupt()` anywhere in graph; resume with input | ⭐⭐⭐ Task callbacks; human approval at task boundaries | ⭐⭐⭐⭐⭐ `UserProxyAgent`; interrupt mid-conversation | ⭐⭐⭐ `UserAgent`; synchronous input |
| **Ease of Use** | ⭐⭐ Steep learning curve | ⭐⭐⭐⭐⭐ Easiest | ⭐⭐⭐ Medium | ⭐⭐ Steep; less documentation |
| **Production Readiness** | ⭐⭐⭐⭐⭐ LangGraph Platform; cloud deployment; enterprise support | ⭐⭐⭐⭐ CrewAI Enterprise; REST API deployment | ⭐⭐⭐⭐ Microsoft backing; AutoGen Studio | ⭐⭐ More research/academic |
| **MCP Support** | ⭐⭐⭐ Via LangChain MCP tools | ⭐⭐⭐⭐⭐ First-class MCP integration (multiple transports) | ⭐⭐⭐ Via extensions | ⭐⭐ Limited |
| **Observability** | ⭐⭐⭐⭐⭐ LangSmith + LangGraph Studio | ⭐⭐⭐⭐ Event listeners + Enterprise dashboard | ⭐⭐⭐⭐ AutoGen Studio + OpenTelemetry | ⭐⭐⭐ AgentScope Studio |
| **Multi-language** | Python + JS/TS | Python | Python + .NET | Python + Java |
| **Async / Parallel** | ⭐⭐⭐⭐⭐ Native parallel edges via `Send()` | ⭐⭐⭐⭐ `async_execution` per task | ⭐⭐⭐⭐⭐ Fully async actor model | ⭐⭐⭐⭐⭐ Distributed actor model |

---

## 6. Scoring for Storytelling AI Use Case

*Requirements: interactive conversation, 6–8 specialized agents with different roles and tool permissions, agent-to-agent debate/validation, RAG (story books vector DB), real-time web search, structured outputs (outline → full script), boss agent, persistent memory.*

| Criterion | Weight | LangGraph | CrewAI | AutoGen | AgentScope |
|---|---|---|---|---|---|
| Hierarchical boss agent | 20% | 10/10 | 9/10 | 8/10 | 5/10 |
| Per-agent tool scoping | 15% | 10/10 | 10/10 | 10/10 | 7/10 |
| Debate/validation between agents | 15% | 7/10 | 5/10 | 8/10 | 7/10 |
| RAG integration ease | 15% | 10/10 | 9/10 | 8/10 | 6/10 |
| Session-persistent memory | 15% | 10/10 | 9/10 | 7/10 | 5/10 |
| Interactive conversation UX | 10% | 9/10 | 7/10 | 9/10 | 7/10 |
| Structured output (outlines/scripts) | 10% | 10/10 | 10/10 | 9/10 | 7/10 |
| **Weighted Total** | | **9.6/10** | **8.6/10** | **8.2/10** | **5.9/10** |

---

## 7. Recommended Architecture

### 🥇 Primary Recommendation: **LangGraph**

**Why LangGraph wins for this use case:**

1. **Boss Agent (Supervisor)** — LangGraph's `supervisor` pattern is the most expressive. A `StoryDirector` node acts as the orchestrator with its own LLM + routing logic, sending `Command(goto="agent_name")` to delegate to specialists. Nesting is supported (sub-supervisors).

2. **Per-Agent Tool Scoping** — Each agent node is its own compiled `create_react_agent(llm, tools=[...])`. The Web Researcher gets Tavily search; the RAG Librarian gets VectorStoreRetriever; the Script Editor gets file tools; none bleed into each other.

3. **RAG** — LangChain's 50+ vector store integrations (Chroma, Pinecone, Weaviate, Qdrant, MongoDB) are all immediately available. The `RAGLibrarian` agent can be a `create_react_agent` with `VectorStoreRetriever` as its only tool. Embedding models selectable per-retriever.

4. **Session-Persistent Memory** — `thread_id`-based checkpointing with SQLite/PostgreSQL means every story session is automatically persisted. The `Store` gives cross-session long-term memory (story Bible, character sheets, worldbuilding notes) that survive across multiple user sessions.

5. **Debate/Validation Loop** — Implement `StoryEditor` → `ContinuityChecker` → conditional edge looping: if checker flags inconsistency, graph routes back to `StoryEditor` for revision. Can add an explicit `ConsensusNode` that aggregates votes from multiple critics using a custom reducer.

6. **Structured Output Pipeline** — State schema enforces: `story_outline: StoryOutline` (Pydantic) → `scene_list: List[Scene]` → `full_script: Script`. Each node validates its output against the schema.

7. **Interactive Conversation** — `interrupt()` at any node allows: "Here's the outline. Approve or request changes?" User input resumes the graph from the interruption point.

8. **Observability** — LangSmith traces every agent call, state snapshot, and edge traversal. Visual debugging of story generation failures.

---

### 🥈 Strong Alternative: **CrewAI** (if you want faster prototyping)

**Why consider CrewAI:**
- **Fastest time to prototype** — Define 8 agents with roles/goals in YAML config, assign tools, run hierarchical crew. Working prototype in ~100 lines.
- **Built-in memory** — `long_term_memory=True` + `knowledge=True` at crew level gives persistent RAG out of the box with near-zero config.
- **Manager agent** — `Process.hierarchical` with `manager_llm=gpt-4o` gives you a boss agent that autonomously plans and delegates.
- **MCP first-class** — Connect MCP servers for rich tool ecosystems.

**CrewAI limitation for storytelling:** Less control over the execution graph. The manager decides task order dynamically, which is great for autonomy but less deterministic. If you need "always produce outline BEFORE script", you need `Process.sequential` + careful task design.

---

### 🥉 Honorable Mention: **AutoGen** (for debate-heavy workflows)

**Why consider AutoGen:**
- `SelectorGroupChat` with a custom `selector_func` is the most natural framework for **structured debate**: define Author, Critic, Fact-Checker, and a Judge agent; selector cycles Author → Critic → Author → Fact-Checker → Judge.
- Broadcasting model (all agents see all messages) is actually great for storytelling: all agents have full context.
- `MagenticOneGroupChat` is a production-ready orchestrator pattern.

**AutoGen limitation:** Memory persistence requires more manual wiring than LangGraph or CrewAI.

---

### ❌ Not Recommended: **AgentScope** (for this use case)

- Research-grade maturity; production story generation needs reliability and ecosystem depth.
- Less integrations for vector DBs and web search.
- Documentation and community smaller.
- Use if you need distributed simulation of many story agents (e.g., NPC swarms in a game world) — that's its sweet spot.

---

## 8. Proposed Storytelling AI Architecture with LangGraph

```
StoryDirector (Supervisor)
├── Routing logic: reads current_phase, last_output, user_intent
├── Commands to: WorldBuilder, CharacterArchitect, PlotWeaver, 
│              RAGLibrarian, WebResearcher, ScriptWriter, 
│              ContinuityChecker, NarratorAgent
│
├── WorldBuilder Agent
│   ├── Tools: RAG (world-lore vector DB), memory Store
│   └── Output: WorldState schema
│
├── CharacterArchitect Agent
│   ├── Tools: RAG (character archetypes DB), entity memory
│   └── Output: CharacterSheet schema
│
├── PlotWeaver Agent
│   ├── Tools: RAG (story structure books), ConflictTool
│   └── Output: StoryOutline schema
│
├── RAGLibrarian Agent
│   ├── Tools: VectorStoreRetriever (story books, tropes, genres)
│   └── Output: RetrievedContext schema
│
├── WebResearcher Agent
│   ├── Tools: TavilySearch, BraveSearch
│   └── Output: ResearchNotes schema
│
├── ScriptWriter Agent
│   ├── Tools: None (pure generation)
│   └── Output: SceneScript schema
│
├── ContinuityChecker Agent (DEBATE)
│   ├── Tools: Read state (worldState, characterSheets)
│   └── Output: ValidationResult (pass/fail + critique)
│
└── NarratorAgent
    ├── Tools: TextToSpeech (optional)
    └── Output: FinalNarration string

State Schema:
  - thread_id → persistent per user session
  - story_phase: Enum[brainstorm, outline, draft, revise, final]
  - world_state: WorldState
  - characters: List[CharacterSheet]
  - story_outline: StoryOutline
  - scene_queue: List[Scene]
  - current_script: Script
  - validation_history: List[ValidationResult]
  - user_messages: List[Message]
  - revision_count: int

Conditional Edges:
  - After ContinuityChecker: pass → ScriptWriter (next scene) 
                              fail + revision_count < 3 → ScriptWriter (revise)
                              fail + revision_count >= 3 → StoryDirector (human input)
  - After PlotWeaver: interrupt() → user approval → continue or branch
  - After NarratorAgent: END or loop back to StoryDirector for next chapter
```

---

## 9. Key Decision Factors Summary

| If you need... | Choose |
|---|---|
| Maximum control over execution flow + best persistence | **LangGraph** |
| Fastest prototyping + built-in memory + easy teams | **CrewAI** |
| Best native debate/critic patterns + conversation UX | **AutoGen** |
| Multi-process distributed agent simulation | **AgentScope** |
| Production + observability + enterprise support | **LangGraph** or **CrewAI** |
| RAG with least config | **CrewAI** (`knowledge=True`) |
| Fine-grained graph control for story phase transitions | **LangGraph** |

**Final Verdict for Conversational Storytelling AI with 6–8 agents:**

> **LangGraph is the best fit.** Its graph-based state machine perfectly models story phase transitions (brainstorm → outline → draft → revise → publish). The supervisor pattern provides a hierarchical boss agent. Thread-based checkpointing gives seamless session persistence. Per-node tool scoping enables fine-grained permissions. The interrupt mechanism enables natural human-in-the-loop conversation. LangChain's ecosystem provides immediate RAG and web search integrations. The only cost is a steeper learning curve — invest ~1–2 weeks in understanding state reducers, subgraphs, and the checkpoint system.

> **If you want to ship a working prototype in 2–3 days, start with CrewAI** in hierarchical mode, then migrate to LangGraph when you need finer control over story phase transitions and memory architecture.
