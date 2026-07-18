"""
Validator Agent — quality gate that scores outlines on 5 criteria.
Provides actionable weak_areas and targeted_question to guide Story Miner
when the outline needs more material from the user.
"""
import re
import json
from datetime import datetime
from langgraph.prebuilt import create_react_agent

from config import settings
from agents.state import ArcwrightState, ValidationResult, AgentNote, ThoughtProcess


_SYSTEM_PROMPT = """You are the Story Validator — a quality gatekeeper for narratives.

You evaluate story outlines on 5 criteria, each scored 0-10 (total max: 50):

1. RELATABILITY (0-10): Will many people connect with this story? Is the core experience universal?
2. EMOTIONAL HOOK (0-10): Does it evoke genuine emotion? Is there a real emotional turning point?
3. ORIGINALITY (0-10): Is the perspective fresh or generic? Does it offer a unique angle?
4. PLATFORM FIT (0-10): Does it match the target platform format, length, and tone?
5. TREND ALIGNMENT (0-10): Is it relevant to current audience interests?

Scoring thresholds:
- ≥35/50: PASS — move forward to user approval
- 25-34/50: REVISE — the outline structure is okay but needs more specific story material
- <25/50: REJECT — the story material itself is too thin or generic

When REVISE or REJECT, you MUST:
1. Identify the SPECIFIC WEAK AREAS (which criteria scored lowest and why)
2. Identify WHAT STORY MATERIAL is missing (specific sensory details? character reactions? turning point clarity?)
3. Write a TARGETED QUESTION that the Story Miner can ask the user to get exactly what's missing

ALWAYS output this exact JSON at the end:
[VALIDATION_RESULT]:
{
  "score": <total 0-50>,
  "criteria_scores": {
    "relatability": <0-10>,
    "emotional_hook": <0-10>,
    "originality": <0-10>,
    "platform_fit": <0-10>,
    "trend_alignment": <0-10>
  },
  "verdict": "PASS" | "REVISE" | "REJECT",
  "feedback": "<specific critique — what exactly needs to improve>",
  "weak_areas": ["<criterion_1>", "<criterion_2>"],
  "targeted_question": "<ONE specific question to ask the user to get missing material — in Indonesian if the session is Indonesian>",
  "missing_material": "<what specific story element is missing: sensory detail / character reaction / turning point specifics / stakes / etc>"
}"""


def validator_node(state: ArcwrightState, llm) -> dict:
    """
    Validator node — scores outline and provides actionable critique.

    Reads:  story_outline, story_fragments, web_research, deep_dive_analysis, rag_results
    Writes: validation_result, debate_rounds, debate_log, agent_notes, targeted_probe_mode
    """
    agent = create_react_agent(
        model=llm,
        tools=[],
        prompt=_SYSTEM_PROMPT,
    )

    outline = state.get("story_outline")
    if not outline:
        return {}

    platform = state.get("user_profile", {}).get("platform_target", "general")
    fragments = state.get("story_fragments", [])
    web = state.get("web_research", [])
    trends = web[0].get("trends", []) if web else []
    deep_dive = state.get("deep_dive_analysis", {})

    # Get RAG-informed quality context
    rag_results = state.get("rag_results", [])
    enriching_rag = next((r for r in reversed(rag_results) if r.get("query_purpose") == "enriching"), None)
    rag_framework = enriching_rag.get("synthesis", "") if enriching_rag else ""

    # Fragment quality summary
    quality_fragments = [f for f in fragments if f.get("quality_score", 0) >= settings.FRAGMENT_QUALITY_THRESHOLD]

    thought = ThoughtProcess(
        agent="validator",
        timestamp=datetime.now().isoformat(),
        thought=f"Scoring outline '{outline.get('title', '')}'. "
                f"{len(quality_fragments)}/{len(fragments)} quality fragments. "
                f"Debate round: {state.get('debate_rounds', 0)}/{settings.MAX_DEBATE_ROUNDS}.",
        data={"outline_title": outline.get("title", ""), "fragment_count": len(fragments)}
    )

    query = f"""Please evaluate this story outline:

OUTLINE:
Title: {outline.get("title", "")}
Hook: {outline.get("hook", "")}
Setup: {outline.get("setup", "")}
Turning Point: {outline.get("turning_point", "")}
Struggle: {outline.get("struggle", "")}
Resolution: {outline.get("resolution", "")}
Punchline: {outline.get("punchline", "")}
Platform: {outline.get("platform", platform)}
Duration: {outline.get("estimated_duration", "")}

SOURCE MATERIAL ({len(quality_fragments)} quality fragments out of {len(fragments)} total):
{chr(10).join(f"- [Q:{f.get('quality_score',0)}/10] {f['text']}" for f in fragments[:6])}

DEEP DIVE ANALYSIS:
- Surface: {deep_dive.get("surface", "N/A")}
- Psychological: {deep_dive.get("psychological", "N/A")}
- Universal theme: {deep_dive.get("universal", "N/A")}
- Hidden gold: {deep_dive.get("hidden_gold", "N/A")}

STORYTELLING FRAMEWORK APPLIED:
{rag_framework[:600] if rag_framework else "No specific framework applied"}

CURRENT TRENDS ({platform}): {", ".join(str(t) for t in trends[:5]) if trends else "No trend data"}

Debate round: {state.get("debate_rounds", 0)}/{settings.MAX_DEBATE_ROUNDS}

Score this outline rigorously. If REVISE or REJECT, provide a specific targeted_question 
that Story Miner can ask the user to get exactly what's missing."""

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    response_text = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
            response_text = msg.content
            break

    validation = _parse_validation(response_text)
    current_rounds = state.get("debate_rounds", 0)

    updates: dict = {
        "validation_result": validation,
        "debate_log": [{
            "round": current_rounds,
            "score": validation["score"],
            "verdict": validation.get("verdict", ""),
            "feedback": validation["feedback"],
            "weak_areas": validation.get("weak_areas", []),
            "targeted_question": validation.get("targeted_question", ""),
        }],
        "thought_process": [thought],
    }

    if not validation["passed"]:
        updates["debate_rounds"] = current_rounds + 1
        updates["agent_notes"] = [AgentNote(
            agent_name="validator",
            note_type="critique",
            content=(
                f"Score: {validation['score']}/50 — {validation['feedback']}\n"
                f"Weak areas: {', '.join(validation.get('weak_areas', []))}\n"
                f"Missing: {validation.get('missing_material', '')}"
            ),
        )]
        # Signal Story Miner untuk masuk targeted probe mode
        updates["targeted_probe_mode"] = True

    return updates


def _parse_validation(text: str) -> ValidationResult:
    """Parse [VALIDATION_RESULT] JSON from agent response."""
    pattern = r"\[VALIDATION_RESULT\]:\s*(\{[\s\S]+?\})\s*$"
    match = re.search(pattern, text)

    if match:
        try:
            data = json.loads(match.group(1))
            score = float(data.get("score", 0))
            return ValidationResult(
                score=score,
                criteria_scores=data.get("criteria_scores", {}),
                feedback=data.get("feedback", ""),
                passed=score >= settings.VALIDATOR_PASS_THRESHOLD,
                weak_areas=data.get("weak_areas", []),
                targeted_question=data.get("targeted_question", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # Fallback: extract score from text
    score_match = re.search(r"(\d+)\s*/\s*50", text)
    score = float(score_match.group(1)) if score_match else 0.0
    return ValidationResult(
        score=score,
        criteria_scores={},
        feedback=text[:500],
        passed=score >= settings.VALIDATOR_PASS_THRESHOLD,
        weak_areas=[],
        targeted_question="",
    )
