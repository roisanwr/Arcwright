# Multi-Agent AI Systems: Best Practices & Design Patterns
> Research compiled for a Storytelling AI with specialist agents  
> Sources: LLM-Debate (Du et al. 2023), Self-Refine (Madaan et al. 2023), Reflexion (Shinn et al. 2023), Constitutional AI (Anthropic 2022), AutoGen (Microsoft), LangGraph (LangChain)

---

## Table of Contents
1. [Agent Permission Systems & Tool Access Control](#1-agent-permission-systems--tool-access-control)
2. [Debate & Consensus Mechanisms](#2-debate--consensus-mechanisms)
3. [Memory Architecture](#3-memory-architecture)
4. [Real-World Validation Patterns](#4-real-world-validation-patterns)
5. [Orchestrator + Specialist Pattern](#5-orchestrator--specialist-pattern)
6. [Applied Design: Storytelling AI](#6-applied-design-storytelling-ai)

---

## 1. Agent Permission Systems & Tool Access Control

### Core Principle: Least Privilege Per Agent

Each agent should have access **only to tools required for its specific role**. This is not just security hygiene — it prevents agents from "escaping" their domain, reduces hallucination surface area, and makes the system easier to audit.

### Permission Taxonomy

```
TIER 0 — READ-ONLY, NO SIDE EFFECTS
  Examples: search_web, read_document, get_story_premise
  Who gets this: All agents (safe baseline)

TIER 1 — WRITE TO SHARED STATE
  Examples: write_to_memory, update_plot_graph, annotate_character
  Who gets this: Agents that contribute structured outputs (Story Agent, Character Agent)

TIER 2 — EXTERNAL I/O
  Examples: call_external_api, send_email, write_to_database
  Who gets this: Orchestrator only, or designated I/O agent

TIER 3 — ORCHESTRATION CONTROL
  Examples: spawn_subagent, call_specialist, terminate_session
  Who gets this: Orchestrator only — never specialists
```

### Practical Pattern: Tool Registry with Agent Roles

```python
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import Enum

class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    STORY_MINER = "story_miner"
    CHARACTER_DESIGNER = "character_designer"
    VALIDATOR = "validator"
    MEMORY_KEEPER = "memory_keeper"
    NARRATOR = "narrator"

@dataclass
class Tool:
    name: str
    fn: Callable
    allowed_roles: set[AgentRole]
    description: str
    side_effects: bool = False  # flags write/external operations

# Define tools with explicit role allowlists
TOOL_REGISTRY = [
    Tool(
        name="search_narrative_database",
        fn=search_narrative_db,
        allowed_roles={AgentRole.STORY_MINER, AgentRole.ORCHESTRATOR},
        description="Search for story patterns and narrative structures",
        side_effects=False
    ),
    Tool(
        name="write_character_profile",
        fn=write_character,
        allowed_roles={AgentRole.CHARACTER_DESIGNER},
        description="Persist a character profile to shared memory",
        side_effects=True
    ),
    Tool(
        name="flag_narrative_inconsistency",
        fn=flag_inconsistency,
        allowed_roles={AgentRole.VALIDATOR},
        description="Mark a narrative element as inconsistent",
        side_effects=True
    ),
    Tool(
        name="call_specialist",
        fn=route_to_specialist,
        allowed_roles={AgentRole.ORCHESTRATOR},  # ONLY orchestrator can route
        description="Route task to a specialist agent",
        side_effects=False
    ),
    Tool(
        name="read_user_memory",
        fn=read_user_context,
        allowed_roles={
            AgentRole.ORCHESTRATOR,
            AgentRole.STORY_MINER,
            AgentRole.NARRATOR
        },
        description="Read persistent user preferences and history",
        side_effects=False
    ),
]

def get_tools_for_agent(role: AgentRole) -> list[Tool]:
    """Filter tool registry to only those allowed for this role."""
    return [t for t in TOOL_REGISTRY if role in t.allowed_roles]

def execute_tool(agent_role: AgentRole, tool_name: str, **kwargs):
    """
    Enforce permission check at call time.
    Raises PermissionError if agent isn't allowed to use tool.
    """
    tool = next((t for t in TOOL_REGISTRY if t.name == tool_name), None)
    if not tool:
        raise ValueError(f"Tool '{tool_name}' not found")
    if agent_role not in tool.allowed_roles:
        raise PermissionError(
            f"Agent '{agent_role.value}' is not allowed to use tool '{tool_name}'. "
            f"Allowed roles: {[r.value for r in tool.allowed_roles]}"
        )
    return tool.fn(**kwargs)
```

### Why This Matters for Storytelling AI

| Agent | Allowed Tools | Rationale |
|-------|--------------|-----------|
| **Orchestrator** | `call_specialist`, `read_user_memory`, `plan_task` | Needs to route and plan, but shouldn't generate content |
| **Story Miner** | `search_narrative_db`, `analyze_theme`, `read_user_memory` | Source material access only; no writing to shared state |
| **Character Designer** | `write_character_profile`, `read_character_profiles`, `check_consistency` | Owns character namespace |
| **Validator** | `flag_inconsistency`, `read_all_agents_output`, `approve_output` | Read-all + veto power, but no direct content creation |
| **Narrator** | `synthesize_narrative`, `read_user_memory`, `format_output` | Output generation only; no database writes |

### Key Anti-Patterns to Avoid
- ❌ **God Agent**: One agent with access to all tools — kills specialization benefits and makes auditing impossible
- ❌ **Tool Sharing Without Gates**: Multiple agents writing to the same memory store without arbitration → race conditions and incoherence
- ❌ **Orchestrator Doing Specialist Work**: If the orchestrator writes content, it can't evaluate it objectively

---

## 2. Debate & Consensus Mechanisms

### The Core Insight: Disagreement Improves Quality

**LLM-Debate (Du et al., 2023, arXiv:2305.14325)**:
> "Multiple language model instances propose and debate their individual responses and reasoning processes over multiple rounds to arrive at a common final answer."
> Key result: **reduces hallucinations** and significantly enhances mathematical and strategic reasoning.

Three distinct patterns for agents to "argue" and reach solutions:

---

### Pattern A: Multi-Round Debate (Society of Minds)

Each agent independently generates a response, then sees others' responses and revises. Iterates until convergence.

```python
import asyncio
from typing import Optional

async def multi_agent_debate(
    question: str,
    agents: list,       # list of LLM agent instances
    rounds: int = 3,
    judge: Optional[object] = None
) -> dict:
    """
    Implementation of Du et al. 2023 debate protocol.
    Each round: all agents see previous round's answers and revise.
    """
    # Round 0: Independent generation (no influence)
    responses = {}
    for agent in agents:
        responses[agent.name] = await agent.generate(
            prompt=question,
            context=None  # blind first round
        )

    debate_history = [dict(responses)]  # track full history

    # Debate rounds: agents see each other and can revise
    for round_num in range(1, rounds + 1):
        # Format other agents' responses as context
        for agent in agents:
            others_context = "\n\n".join([
                f"Agent {name} argued: {resp}"
                for name, resp in responses.items()
                if name != agent.name
            ])
            
            prompt = f"""
Original question: {question}

Other agents have argued:
{others_context}

Given these perspectives, do you maintain your position or revise it?
Provide your updated reasoning and answer.
If you change your answer, explain why the other arguments convinced you.
"""
            responses[agent.name] = await agent.generate(prompt=prompt)
        
        debate_history.append(dict(responses))
        
        # Early convergence check: if all agents agree, stop
        answers = list(responses.values())
        if len(set(answers)) == 1:
            break
    
    # Resolution: Judge agent or majority vote
    if judge:
        final = await judge.synthesize(
            question=question,
            debate_history=debate_history
        )
    else:
        final = majority_vote(responses)
    
    return {
        "final_answer": final,
        "debate_history": debate_history,
        "rounds_completed": round_num,
        "consensus_reached": len(set(responses.values())) == 1
    }

def majority_vote(responses: dict) -> str:
    """Simple majority vote for consensus."""
    from collections import Counter
    counts = Counter(responses.values())
    return counts.most_common(1)[0][0]
```

---

### Pattern B: Adversarial Agents (Devil's Advocate)

One agent proposes; a dedicated adversarial agent tries to find flaws; a judge decides. This is the pattern most relevant to your **Validator vs Story Mining** debate.

```python
class AdversarialDebate:
    """
    Structured adversarial debate between Proposer and Critic.
    Inspired by Constitutional AI critique-revision cycle.
    """
    
    def __init__(self, proposer, critic, judge, max_rounds=3):
        self.proposer = proposer  # Story Mining agent
        self.critic = critic      # Validator agent
        self.judge = judge        # Orchestrator or dedicated judge
        self.max_rounds = max_rounds
    
    async def debate(self, story_angle: str, user_context: dict) -> dict:
        """
        Validator debates Story Miner about whether a story angle is good.
        Returns approved/rejected + reasoning.
        """
        proposal = story_angle
        debate_log = []
        
        for round_num in range(self.max_rounds):
            # Critic challenges the proposal
            critique = await self.critic.critique(
                proposal=proposal,
                criteria=[
                    "Does this angle serve the user's stated preferences?",
                    "Is this internally consistent with established lore?",
                    "Does this avoid common narrative clichés?",
                    "Is the conflict meaningful, not arbitrary?",
                ],
                user_context=user_context
            )
            
            debate_log.append({"round": round_num, "critique": critique})
            
            # If critic has no issues, we're done
            if critique["severity"] == "none":
                return {
                    "approved": True,
                    "final_proposal": proposal,
                    "debate_log": debate_log
                }
            
            # Proposer responds to critique and revises
            revision = await self.proposer.revise(
                original=proposal,
                critique=critique["issues"],
                instructions="Address each critique point specifically."
            )
            
            debate_log.append({"round": round_num, "revision": revision})
            proposal = revision["revised_proposal"]
        
        # After max rounds, judge decides
        verdict = await self.judge.decide(
            original=story_angle,
            final_proposal=proposal,
            debate_log=debate_log
        )
        
        return {
            "approved": verdict["approved"],
            "final_proposal": proposal if verdict["approved"] else story_angle,
            "judge_reasoning": verdict["reasoning"],
            "debate_log": debate_log
        }
```

---

### Pattern C: Voting with Confidence Weighting

Better than pure majority vote when agents have different expertise levels.

```python
async def weighted_consensus(
    question: str,
    agents: list,
    weights: Optional[dict] = None  # {agent_name: weight}
) -> dict:
    """
    Weighted voting where specialist agents have higher authority
    in their domain.
    """
    responses = {}
    for agent in agents:
        result = await agent.generate(question)
        responses[agent.name] = {
            "answer": result["answer"],
            "confidence": result.get("confidence", 0.5),  # 0-1
            "reasoning": result["reasoning"]
        }
    
    # Apply domain weights + self-reported confidence
    scores = {}
    for agent_name, response in responses.items():
        domain_weight = weights.get(agent_name, 1.0) if weights else 1.0
        effective_weight = domain_weight * response["confidence"]
        answer = response["answer"]
        scores[answer] = scores.get(answer, 0) + effective_weight
    
    winner = max(scores, key=scores.get)
    total_weight = sum(scores.values())
    
    return {
        "consensus_answer": winner,
        "confidence_score": scores[winner] / total_weight,
        "all_votes": scores,
        "dissenting_agents": [
            name for name, r in responses.items()
            if r["answer"] != winner
        ]
    }
```

### When to Use Which Pattern

| Scenario | Best Pattern | Why |
|----------|-------------|-----|
| "Is this story angle good?" | **Adversarial (B)** | Binary quality gate, specific criteria |
| "What should happen next?" | **Multi-round Debate (A)** | Open-ended creative choice benefits from iteration |
| "Which of these 3 endings is best?" | **Weighted Voting (C)** | Comparative evaluation with domain expertise |
| "Does this violate lore?" | **Adversarial (B)** | Validator has veto authority on consistency |

---

## 3. Memory Architecture

### The Four-Layer Memory Model

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: LONG-TERM PERSISTENT MEMORY (User across sessions)│
│  Storage: Vector DB + Structured JSON                        │
│  Scope: All agents can READ; Memory Keeper writes           │
│  Contains: preferences, character history, world state       │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: SESSION MEMORY (Current conversation)              │
│  Storage: In-memory message history / LangGraph state        │
│  Scope: All agents share via message bus                     │
│  Contains: what user said this session, decisions made       │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: AGENT SCRATCHPAD (Per-agent working memory)        │
│  Storage: Private per-agent context window                   │
│  Scope: Private to each agent                                │
│  Contains: intermediate reasoning, draft outputs             │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1: TOOL OUTPUT CACHE (Short-term ephemeral)           │
│  Storage: In-memory dict, expires after task                 │
│  Scope: Current task only                                    │
│  Contains: search results, API responses                     │
└─────────────────────────────────────────────────────────────┘
```

### Implementation: Shared + Private Memory Split

```python
from dataclasses import dataclass, field
from typing import Any
import json
from datetime import datetime

@dataclass
class SharedMemoryStore:
    """
    Thread-safe shared memory accessible by all agents.
    Implements the 'blackboard' pattern from distributed AI.
    """
    # Structured world state
    story_world: dict = field(default_factory=dict)
    characters: dict = field(default_factory=dict)
    plot_decisions: list = field(default_factory=list)
    validated_elements: set = field(default_factory=set)
    
    # User context (persisted across sessions)
    user_preferences: dict = field(default_factory=dict)
    user_history: list = field(default_factory=list)  # past sessions summary
    
    # Debate/validation audit trail
    validation_log: list = field(default_factory=list)
    
    def write(self, key: str, value: Any, author: AgentRole, requires_validation: bool = False):
        """Write to shared memory. High-stakes writes require validation flag."""
        entry = {
            "key": key,
            "value": value,
            "author": author.value,
            "timestamp": datetime.utcnow().isoformat(),
            "validated": not requires_validation,
            "pending_validation": requires_validation
        }
        # Store by key
        setattr(self, key, value)
        self.validation_log.append(entry)
    
    def read(self, key: str, agent: AgentRole) -> Any:
        """Read from shared memory. Logs access for audit."""
        return getattr(self, key, None)
    
    def approve_pending(self, key: str, approver: AgentRole):
        """Validator approves a pending memory write."""
        if approver != AgentRole.VALIDATOR:
            raise PermissionError("Only Validator can approve pending writes")
        for entry in self.validation_log:
            if entry["key"] == key and entry["pending_validation"]:
                entry["pending_validation"] = False
                entry["validated"] = True
                entry["approved_by"] = approver.value


@dataclass  
class AgentScratchpad:
    """
    Private per-agent memory. Never visible to other agents.
    Acts as the agent's 'working memory' / chain-of-thought space.
    """
    agent_name: str
    _private_notes: list = field(default_factory=list)
    _draft_outputs: list = field(default_factory=list)
    _tool_cache: dict = field(default_factory=dict)
    
    def note(self, content: str):
        """Agent's private reasoning notes."""
        self._private_notes.append({
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def draft(self, output: str):
        """Store a draft output before committing to shared memory."""
        self._draft_outputs.append(output)
    
    def cache_tool_result(self, tool_name: str, result: Any):
        """Cache tool results for this task to avoid re-fetching."""
        self._tool_cache[tool_name] = result
```

### User Context Continuity Across Conversations

This is one of the hardest problems in multi-agent systems. The pattern that works:

```python
class UserContextManager:
    """
    Maintains user identity and preferences across multiple sessions.
    Each new session loads relevant context from long-term storage.
    """
    
    def __init__(self, user_id: str, vector_store, structured_store):
        self.user_id = user_id
        self.vector_store = vector_store      # semantic memory (ChromaDB, Pinecone)
        self.structured_store = structured_store  # JSON/SQL for facts
    
    def load_session_context(self, current_topic: str) -> dict:
        """
        At session start: load relevant memories.
        Uses semantic search to find RELEVANT past context, not just recent.
        """
        # Semantic: "What do we know related to this topic?"
        relevant_memories = self.vector_store.similarity_search(
            query=current_topic,
            filter={"user_id": self.user_id},
            k=5
        )
        
        # Structured: Always load core facts
        user_facts = self.structured_store.get(self.user_id, {})
        
        return {
            "user_id": self.user_id,
            "name": user_facts.get("name"),
            "preferences": user_facts.get("storytelling_preferences", {}),
            "established_characters": user_facts.get("characters", []),
            "world_rules": user_facts.get("world_rules", []),
            "relevant_past_stories": [m.page_content for m in relevant_memories],
            "session_count": user_facts.get("session_count", 0)
        }
    
    def save_session_summary(self, session_data: dict):
        """
        At session end: extract and persist what matters.
        Don't save raw conversation — compress to facts + semantic chunks.
        """
        summary = {
            "session_date": datetime.utcnow().isoformat(),
            "story_decisions": session_data.get("plot_decisions", []),
            "new_characters": session_data.get("new_characters", []),
            "user_reactions": session_data.get("user_reactions", []),
            "world_changes": session_data.get("world_changes", []),
        }
        
        # Save structured facts
        self.structured_store.update(self.user_id, {
            "session_count": self.structured_store.get(self.user_id, {}).get("session_count", 0) + 1,
            "characters": session_data.get("all_characters", []),
        })
        
        # Save semantic memory (for similarity search in future sessions)
        self.vector_store.add_texts(
            texts=[json.dumps(summary)],
            metadatas=[{"user_id": self.user_id, "type": "session_summary"}]
        )
```

### Memory Access Patterns Summary

| Memory Type | Scope | Persistence | Who Writes | Who Reads |
|-------------|-------|-------------|------------|-----------|
| **User Long-Term** | Cross-session | Permanent | Memory Keeper | All agents |
| **Session State** | Single session | Ephemeral | All agents (gated) | All agents |
| **Agent Scratchpad** | Single task | Ephemeral | Self only | Self only |
| **Tool Cache** | Single tool call | Ephemeral | Auto (system) | Same agent |
| **Debate Log** | Single debate | Session | Auto (system) | Validator, Judge |

---

## 4. Real-World Validation Patterns

### 4A. Constitutional AI (Anthropic, 2022)

**What it is**: A critique-revision loop where the model itself acts as judge against a written "constitution" (a set of principles).

**Two-phase process**:
1. **SL Phase**: Model generates → critiques against principles → revises → finetune on revisions
2. **RL Phase**: RLAIF (RL from AI Feedback) — another model scores outputs against constitution

**Applied to Storytelling AI**:
```python
STORYTELLING_CONSTITUTION = [
    "The story should respect character consistency established in previous sessions.",
    "New plot developments should not contradict established world rules.",
    "The narrative should honor the user's stated genre preferences.",
    "Character motivations should be internally coherent.",
    "Violence and conflict should serve the story, not be gratuitous.",
]

async def constitutional_revision(draft_story: str, user_context: dict) -> dict:
    """Single-agent self-critique + revision against constitution."""
    
    critiques = []
    for principle in STORYTELLING_CONSTITUTION:
        critique = await llm.generate(f"""
Review this story draft against the following principle:
PRINCIPLE: {principle}

STORY DRAFT:
{draft_story}

USER CONTEXT:
{json.dumps(user_context, indent=2)}

Does the draft violate this principle? If yes, explain how and suggest a fix.
Response format: {{"violation": true/false, "explanation": "...", "suggested_fix": "..."}}
""")
        critiques.append(json.loads(critique))
    
    violations = [c for c in critiques if c["violation"]]
    
    if not violations:
        return {"approved": True, "draft": draft_story}
    
    # Revision pass
    revision_prompt = f"""
Revise this story draft to address the following issues:

ORIGINAL DRAFT:
{draft_story}

ISSUES TO FIX:
{json.dumps(violations, indent=2)}

Produce a revised version that addresses ALL issues while maintaining narrative quality.
"""
    revised = await llm.generate(revision_prompt)
    return {"approved": True, "draft": revised, "revisions_made": violations}
```

---

### 4B. Self-Refine (Madaan et al., 2023, arXiv:2303.17651)

**What it is**: Single LLM generates → provides feedback on its own output → refines → repeat. No training required. ~20% improvement over single-pass on diverse tasks.

**Key insight**: Same model acts as generator AND critic — this works because critique is easier than generation.

```python
async def self_refine(
    task: str,
    max_iterations: int = 3,
    stop_condition: str = "STOP"
) -> dict:
    """
    Self-Refine loop: generate → feedback → refine → repeat.
    From Madaan et al. 2023.
    """
    output = await llm.generate(task)
    history = [{"iteration": 0, "output": output, "feedback": None}]
    
    for iteration in range(1, max_iterations + 1):
        # Self-feedback phase
        feedback = await llm.generate(f"""
You produced this output for the task: {task}

OUTPUT:
{output}

Provide specific, actionable feedback on how to improve this output.
If the output is already excellent and no improvement is needed, respond with exactly: "{stop_condition}"
Otherwise, list 2-3 concrete improvements.
""")
        
        if feedback.strip() == stop_condition:
            break
        
        # Refinement phase
        output = await llm.generate(f"""
Task: {task}

Current output:
{output}

Feedback to address:
{feedback}

Produce an improved version that specifically addresses the feedback.
""")
        
        history.append({
            "iteration": iteration,
            "output": output,
            "feedback": feedback
        })
    
    return {"final_output": output, "history": history, "iterations": iteration}
```

---

### 4C. Reflexion (Shinn et al., 2023, arXiv:2303.11366)

**What it is**: Agent acts → evaluates outcome → writes verbal reflection → stores in episodic memory → uses memory in next attempt. Achieved **91% pass@1 on HumanEval** (vs GPT-4's 80%).

**Key difference from Self-Refine**: Reflexion uses **persistent memory across attempts** — the agent learns from failures and doesn't repeat them.

```python
@dataclass
class ReflexionAgent:
    """
    Agent that learns from failures through verbal reflection.
    Memory persists across attempts (unlike Self-Refine).
    """
    llm: Any
    episodic_memory: list = field(default_factory=list)  # persists across attempts
    max_attempts: int = 5
    
    async def attempt_task(self, task: str, evaluator: Callable) -> dict:
        """
        Attempt task up to max_attempts times.
        Each failure generates a reflection stored in episodic memory.
        """
        for attempt_num in range(self.max_attempts):
            # Build context from past reflections
            memory_context = ""
            if self.episodic_memory:
                memory_context = "LESSONS FROM PREVIOUS ATTEMPTS:\n" + "\n".join([
                    f"- Attempt {m['attempt']}: {m['reflection']}"
                    for m in self.episodic_memory
                ])
            
            # Generate response with memory context
            response = await self.llm.generate(f"""
Task: {task}

{memory_context}

Based on what you've learned, produce your best response:
""")
            
            # Evaluate outcome
            score, feedback = evaluator(response, task)
            
            if score >= 0.9:  # Success threshold
                return {
                    "success": True,
                    "response": response,
                    "attempts": attempt_num + 1,
                    "episodic_memory": self.episodic_memory
                }
            
            # Failure: generate verbal reflection for memory
            reflection = await self.llm.generate(f"""
I attempted this task: {task}
My response: {response}
Evaluator feedback: {feedback}

Write a brief reflection on what went wrong and what I should do differently.
Be specific about the mistake and the lesson learned.
""")
            
            self.episodic_memory.append({
                "attempt": attempt_num + 1,
                "response": response,
                "feedback": feedback,
                "reflection": reflection,
                "score": score
            })
        
        return {
            "success": False,
            "best_response": max(self.episodic_memory, key=lambda x: x["score"])["response"],
            "attempts": self.max_attempts,
            "episodic_memory": self.episodic_memory
        }
```

---

### 4D. LLM-Debate (Du et al., 2023, arXiv:2305.14325)

**What it is**: Multiple LLM instances independently generate answers, then see each other's responses and debate over multiple rounds. Final answer via voting or synthesis.

**Key results**:
- Significantly reduces hallucinations vs single agent
- Improves mathematical and strategic reasoning
- Works on black-box models (no fine-tuning needed)

The core mechanism: agents are **more likely to maintain a correct answer when challenged** than to abandon it — but will update if other agents provide compelling arguments.

---

### Comparison Table

| Pattern | Agents Needed | Best For | Key Mechanism |
|---------|--------------|----------|---------------|
| **Constitutional AI** | 1 (self-critique) | Safety/quality gates | Constitution as external ruleset |
| **Self-Refine** | 1 (self-loop) | Iterative quality improvement | Generate → Feedback → Refine |
| **Reflexion** | 1 (with memory) | Tasks with multiple attempts | Verbal memory of past failures |
| **LLM-Debate** | 2+ (multi-agent) | Factuality, complex reasoning | Peer pressure + argumentation |
| **Constitutional AI + Multi-Agent** | 2+ | Storytelling AI | Best of both worlds |

---

## 5. Orchestrator + Specialist Pattern

### How the Orchestrator Decides: The 4-Factor Routing Model

An orchestrator uses these signals to decide **which specialist to call and when**:

1. **Intent Classification**: What type of task is this? (story generation, character design, validation, narration)
2. **State Machine**: What's the current workflow stage? (some agents only fire at specific stages)
3. **Capability Matching**: Which agent has the tools/context for this specific subtask?
4. **Load/Priority**: Is an agent already busy with a long task? Can tasks run in parallel?

```python
from enum import Enum
from typing import Optional
import asyncio

class WorkflowStage(Enum):
    INTAKE = "intake"              # understand user request
    STORY_MINING = "story_mining"  # find/generate story material
    CHARACTER_DESIGN = "character_design"
    PLOT_PLANNING = "plot_planning"
    VALIDATION = "validation"      # consistency + quality check
    NARRATION = "narration"        # final output synthesis
    MEMORY_UPDATE = "memory_update"  # persist to long-term

class OrchestratorAgent:
    """
    Central orchestrator that routes to specialist agents.
    Implements: intent classification + state machine + capability matching.
    """
    
    def __init__(self, specialists: dict[str, Any], shared_memory: SharedMemoryStore):
        self.specialists = specialists
        self.shared_memory = shared_memory
        self.llm = None  # orchestrator's own LLM
        self.workflow_graph = self._build_workflow_graph()
    
    def _build_workflow_graph(self) -> dict:
        """
        Define valid stage transitions.
        Orchestrator follows this graph — can't skip validation, for example.
        """
        return {
            WorkflowStage.INTAKE: [WorkflowStage.STORY_MINING, WorkflowStage.CHARACTER_DESIGN],
            WorkflowStage.STORY_MINING: [WorkflowStage.VALIDATION, WorkflowStage.PLOT_PLANNING],
            WorkflowStage.CHARACTER_DESIGN: [WorkflowStage.VALIDATION],
            WorkflowStage.PLOT_PLANNING: [WorkflowStage.VALIDATION],
            WorkflowStage.VALIDATION: [WorkflowStage.NARRATION, WorkflowStage.STORY_MINING],  # can loop back
            WorkflowStage.NARRATION: [WorkflowStage.MEMORY_UPDATE],
            WorkflowStage.MEMORY_UPDATE: []  # terminal
        }
    
    async def classify_intent(self, user_message: str) -> dict:
        """
        Use LLM to classify what the user wants and map to workflow entry points.
        This is the orchestrator's FIRST decision.
        """
        classification = await self.llm.generate(f"""
Classify this user message for a storytelling AI system.

USER MESSAGE: {user_message}

Determine:
1. primary_intent: one of [new_story, continue_story, new_character, modify_character, describe_scene, world_building, other]
2. requires_agents: list of agents needed from [story_miner, character_designer, narrator, validator]
3. can_parallelize: which agents can run simultaneously vs must be sequential
4. estimated_complexity: low/medium/high
5. entry_stage: which workflow stage to start at

Respond as JSON.
""")
        return json.loads(classification)
    
    async def route_and_execute(self, user_message: str, user_context: dict) -> dict:
        """
        Main orchestration loop.
        """
        # Step 1: Classify intent
        intent = await self.classify_intent(user_message)
        current_stage = WorkflowStage(intent["entry_stage"].replace("_", "_").lower())
        
        results = {}
        
        # Step 2: Execute workflow stages
        while current_stage is not None:
            stage_result = await self._execute_stage(current_stage, user_context, results)
            results[current_stage.value] = stage_result
            
            # Step 3: Decide next stage based on results
            next_stage = await self._decide_next_stage(
                current_stage=current_stage,
                stage_result=stage_result,
                intent=intent
            )
            current_stage = next_stage
        
        return results
    
    async def _execute_stage(self, stage: WorkflowStage, context: dict, prior_results: dict) -> dict:
        """Execute a single workflow stage, routing to appropriate specialist(s)."""
        
        stage_to_specialist = {
            WorkflowStage.STORY_MINING: "story_miner",
            WorkflowStage.CHARACTER_DESIGN: "character_designer",
            WorkflowStage.VALIDATION: "validator",
            WorkflowStage.NARRATION: "narrator",
            WorkflowStage.MEMORY_UPDATE: "memory_keeper",
        }
        
        specialist_name = stage_to_specialist.get(stage)
        if not specialist_name:
            return {}
        
        specialist = self.specialists[specialist_name]
        
        # Build task for specialist — orchestrator translates between agents
        task = {
            "stage": stage.value,
            "user_context": context,
            "prior_results": prior_results,
            "shared_memory": self.shared_memory
        }
        
        return await specialist.execute(task)
    
    async def _decide_next_stage(
        self, 
        current_stage: WorkflowStage, 
        stage_result: dict, 
        intent: dict
    ) -> Optional[WorkflowStage]:
        """
        Orchestrator decides what happens next.
        Uses both deterministic rules AND LLM judgment for ambiguous cases.
        """
        valid_next = self.workflow_graph[current_stage]
        
        if not valid_next:
            return None  # Terminal stage
        
        # Deterministic rules (always apply these first)
        if current_stage == WorkflowStage.VALIDATION:
            if stage_result.get("approved"):
                return WorkflowStage.NARRATION
            else:
                # Validation failed — loop back based on what failed
                failed_type = stage_result.get("failed_type", "story")
                if failed_type == "character":
                    return WorkflowStage.CHARACTER_DESIGN
                return WorkflowStage.STORY_MINING
        
        if current_stage == WorkflowStage.NARRATION:
            return WorkflowStage.MEMORY_UPDATE
        
        # LLM judgment for ambiguous transitions
        decision = await self.llm.generate(f"""
Current stage completed: {current_stage.value}
Stage result summary: {json.dumps({k: str(v)[:100] for k, v in stage_result.items()})}
User intent: {json.dumps(intent)}
Valid next stages: {[s.value for s in valid_next]}

Which stage should run next, and why?
Respond as: {{"next_stage": "stage_name", "reasoning": "..."}}
""")
        
        parsed = json.loads(decision)
        return WorkflowStage(parsed["next_stage"])
```

### AutoGen's SelectorGroupChat: LLM-Based Speaker Selection

AutoGen's `SelectorGroupChat` is a production implementation of orchestrator-style routing:

```python
# AutoGen SelectorGroupChat — real production code pattern
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination

# Define specialists with role descriptions
story_miner = AssistantAgent(
    "StoryMiner",
    model_client=model_client,
    system_message="""You are a Story Mining specialist. 
    You analyze themes, find narrative patterns, and propose story angles.
    Call on VALIDATOR after proposing an angle.
    Call on NARRATOR when a story angle has been approved.""",
    tools=get_tools_for_agent(AgentRole.STORY_MINER)
)

validator = AssistantAgent(
    "Validator",
    model_client=model_client,
    system_message="""You are a Narrative Validator. 
    You check story proposals for: consistency, user preference alignment, and quality.
    You can APPROVE or REJECT with specific reasons.
    After validation, call on ORCHESTRATOR to decide next step.""",
    tools=get_tools_for_agent(AgentRole.VALIDATOR)
)

narrator = AssistantAgent(
    "Narrator",
    model_client=model_client, 
    system_message="""You are the Narrator. 
    You synthesize approved story elements into compelling prose.
    You have the final word on style and tone.""",
    tools=get_tools_for_agent(AgentRole.NARRATOR)
)

# SelectorGroupChat uses an LLM to pick the next speaker
# based on the conversation context — this IS the orchestration logic
team = SelectorGroupChat(
    participants=[story_miner, validator, narrator],
    model_client=model_client,  # LLM that selects next speaker
    selector_prompt="""
You are managing a storytelling AI workflow.
Select the next agent to speak based on the conversation context.

Rules:
- StoryMiner speaks first to propose a story angle
- Validator always reviews before Narrator can speak
- Narrator only speaks after Validator has approved
- If Validator rejects, StoryMiner must revise before resubmitting

Available agents: {agent_names}
Current conversation: {history}
Next speaker:""",
    termination_condition=TextMentionTermination("STORY_COMPLETE")
)
```

### OpenAI Swarm: Handoff-Based Routing (No Central Orchestrator)

An alternative to centralized orchestration — agents hand off to each other directly:

```python
# AutoGen Swarm pattern — agents route themselves via HandoffMessage
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm

story_agent = AssistantAgent(
    "StoryAgent",
    system_message="""
    You create story proposals.
    When done, ALWAYS hand off to ValidatorAgent for review.
    Use: transfer_to_ValidatorAgent()
    """,
    handoffs=["ValidatorAgent"],
    tools=[...]
)

validator_agent = AssistantAgent(
    "ValidatorAgent",
    system_message="""
    You validate story proposals.
    If APPROVED: hand off to NarratorAgent.
    If REJECTED: hand off back to StoryAgent with specific feedback.
    """,
    handoffs=["NarratorAgent", "StoryAgent"],
    tools=[...]
)

# Key: all agents share the same message context
# Handoffs are explicit function calls — not LLM routing
swarm = Swarm(participants=[story_agent, validator_agent, narrator_agent])
```

**Centralized Orchestrator vs. Swarm Handoffs**:

| Aspect | Centralized Orchestrator | Swarm Handoffs |
|--------|------------------------|----------------|
| **Control** | Single point of routing decisions | Distributed — each agent decides |
| **Auditability** | Easy to trace decisions | Harder — logic spread across agents |
| **Flexibility** | Orchestrator can adapt globally | Each agent has local view only |
| **Failure modes** | Orchestrator is SPOF | More resilient, but harder to debug |
| **Best for** | Complex multi-step workflows | Simpler, well-defined handoff chains |
| **Storytelling AI** | ✅ Recommended — complex creative workflow | Works for simpler pipelines |

---

## 6. Applied Design: Storytelling AI

### Recommended Architecture

```
USER INPUT
    │
    ▼
┌─────────────────────────────────────────┐
│           ORCHESTRATOR                   │
│  - Intent classification                 │
│  - Workflow state management             │
│  - Debate arbitration                    │
│  Tools: call_specialist, read_user_memory│
└─────────────────────────────────────────┘
    │           │           │           │
    ▼           ▼           ▼           ▼
┌───────┐ ┌─────────┐ ┌─────────┐ ┌───────┐
│STORY  │ │CHARACTER│ │VALIDATOR│ │MEMORY │
│MINER  │ │DESIGNER │ │         │ │KEEPER │
│       │ │         │ │         │ │       │
│Tools: │ │Tools:   │ │Tools:   │ │Tools: │
│search │ │write_   │ │read_all │ │write_ │
│_db    │ │profile  │ │flag_    │ │long_  │
│analyze│ │read_    │ │inconsist│ │term   │
│_theme │ │profiles │ │approve_ │ │compress│
└───────┘ └─────────┘ │output   │ └───────┘
                       └─────────┘
                           │
                           ▼
                    ┌─────────┐
                    │NARRATOR │
                    │         │
                    │Tools:   │
                    │synthesize│
                    │format   │
                    └─────────┘
```

### The Validator-Story Miner Debate: Concrete Protocol

```python
# This is the key debate pattern for your system:
# Validator debates Story Miner about whether a story angle is good

VALIDATOR_CRITERIA = {
    "consistency": "Does this angle contradict established world rules or character history?",
    "user_alignment": "Does this serve the user's stated genre, tone, and preference?",  
    "narrative_quality": "Is the conflict meaningful? Is there a clear arc?",
    "novelty": "Does this avoid clichés or has the user seen this before?",
    "completability": "Can this story be resolved satisfyingly within reasonable length?"
}

async def story_miner_validator_debate(
    proposed_angle: str,
    story_miner: Any,
    validator: Any,
    orchestrator: Any,
    user_context: dict,
    max_rounds: int = 3
) -> dict:
    """
    Story Miner proposes → Validator critiques → Story Miner revises → repeat.
    Orchestrator arbitrates if no consensus after max_rounds.
    """
    current_angle = proposed_angle
    
    for round_num in range(max_rounds):
        # Validator evaluates
        validation = await validator.evaluate(
            proposal=current_angle,
            criteria=VALIDATOR_CRITERIA,
            user_context=user_context
        )
        
        if validation["approved"]:
            return {
                "status": "approved",
                "final_angle": current_angle,
                "rounds": round_num + 1,
                "validation_score": validation["score"]
            }
        
        # Story Miner defends or revises
        miner_response = await story_miner.respond_to_critique(
            original_angle=current_angle,
            critique=validation["issues"],
            user_context=user_context
        )
        
        if miner_response["action"] == "defend":
            # Miner thinks validator is wrong — escalate to orchestrator
            verdict = await orchestrator.arbitrate(
                proposal=current_angle,
                validator_critique=validation["issues"],
                miner_defense=miner_response["defense"],
                user_context=user_context
            )
            return {
                "status": "arbitrated",
                "final_angle": current_angle if verdict["approved"] else None,
                "orchestrator_reasoning": verdict["reasoning"],
                "rounds": round_num + 1
            }
        
        # Miner revised — loop continues
        current_angle = miner_response["revised_angle"]
    
    # Max rounds hit without consensus — orchestrator decides
    final_verdict = await orchestrator.arbitrate(
        proposal=current_angle,
        context=f"After {max_rounds} debate rounds, no consensus reached",
        user_context=user_context
    )
    
    return {
        "status": "timeout_arbitrated",
        "final_angle": current_angle if final_verdict["approved"] else proposed_angle,
        "rounds": max_rounds
    }
```

### Memory Strategy for Storytelling AI

```python
# At the start of each user session:
session_context = user_context_manager.load_session_context(
    current_topic=user_message  # semantic search finds relevant past sessions
)

# Inject into shared memory for all agents:
shared_memory.write(
    key="user_context",
    value=session_context,
    author=AgentRole.ORCHESTRATOR
)

# Key things to persist across sessions:
# - Character profiles (names, traits, relationships, past decisions)
# - World rules (magic systems, setting constraints, tone)
# - User preferences (favorite genres, pacing, explicit content settings)
# - Story history (major events, unresolved plot threads)
# - Emotional reactions (what the user loved/hated in past sessions)
```

### The 5 Design Decisions Summarized

| Question | Recommendation | Rationale |
|----------|---------------|-----------|
| **Master orchestrator?** | ✅ Yes, with LLM-based intent classification | Creative workflows are too complex for pure rule-based routing |
| **Can agents debate?** | ✅ Yes — Adversarial pattern (Validator vs Story Miner) | Quality improves when decisions are challenged |
| **How is memory shared?** | Shared read, gated write — Memory Keeper owns persistence | Prevents incoherence from concurrent writes |
| **Exclusive vs shared tools?** | Exclusive writes by owner; shared reads for all | Avoids conflicts; each agent owns its namespace |
| **Orchestrator decides routing?** | Yes — via intent classification + state machine + LLM judgment | Combines speed of rules with flexibility of LLM |

---

## References

| Paper | What It Contributes |
|-------|---------------------|
| Du et al. (2023). *Improving Factuality through Multiagent Debate*. arXiv:2305.14325 | Multi-round debate reduces hallucinations, improves reasoning |
| Madaan et al. (2023). *Self-Refine: Iterative Refinement with Self-Feedback*. arXiv:2303.17651 | Single-agent generate→feedback→refine loop, no training required |
| Shinn et al. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning*. arXiv:2303.11366 | Verbal memory of failures enables learning across attempts |
| Anthropic (2022). *Constitutional AI: Harmlessness from AI Feedback* | Self-critique against written principles; RLAIF |
| Microsoft AutoGen (2024). *SelectorGroupChat, Swarm* | Production implementations of orchestrator and handoff patterns |
| LangChain (2024). *LangGraph Multi-Agent Workflows* | Graph-based state management for multi-agent systems |
| Chan et al. (2024). *Visibility into AI Agents*. arXiv:2401.13138 | Permission systems, monitoring, and governance for AI agents |
