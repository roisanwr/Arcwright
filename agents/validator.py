"""
Validator Agent — quality gate that scores outlines on 5 criteria.
Engages in debate with Story Miner when score is below threshold.
"""
import re
import json
from langgraph.prebuilt import create_react_agent

from config import settings
from agents.state import ArcwrightState, ValidationResult, AgentNote


_SYSTEM_PROMPT = """You are the Story Validator — a quality gatekeeper for narratives.

You evaluate story outlines on 5 criteria, each scored 0-10 (total max: 50):

1. RELATABILITY (0-10): Will many people connect with this story? Is the core experience universal?
2. EMOTIONAL HOOK (0-10): Does it evoke genuine emotion? Is there a real emotional turning point?
3. ORIGINALITY (0-10): Is the perspective fresh or generic? Does it offer a unique angle?
4. PLATFORM FIT (0-10): Does it match the target platform format, length, and tone?
5. TREND ALIGNMENT (0-10): Is it relevant to current audience interests?

Scoring thresholds:
- ≥35/50: PASS — move forward to user approval
- 25-34/50: REVISE — provide specific, actionable feedback
- <25/50: REJECT — explain why it won't resonate

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
  "feedback": "<specific, actionable critique — what exactly needs to improve and why>"
}

When REVISE or REJECT: be constructive. Your goal is to IMPROVE the story, not kill it.
Point to specific weaknesses with concrete suggestions."""


def validator_node(state: ArcwrightState, llm) -> dict:
    """
    Validator node — scores outline and decides debate routing.

    Reads:  story_outline, story_fragments, web_research, deep_dive_analysis
    Writes: validation_result, debate_rounds, debate_log, agent_notes
    """
    agent = create_react_agent(
        model=llm,
        tools=[],
        state_modifier=_SYSTEM_PROMPT,
    )

    outline = state.get("story_outline")
    if not outline:
        # Nothing to validate yet
        return {}

    platform = state.get("user_profile", {}).get("platform_target", "general")
    fragments = state.get("story_fragments", [])
    web = state.get("web_research", [])
    trends = web[0].get("trends", []) if web else []

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

SOURCE MATERIAL:
{chr(10).join(f"- {f['text']}" for f in fragments[:5])}

CURRENT TRENDS ({platform}): {", ".join(str(t) for t in trends[:5]) if trends else "No trend data available"}

Debate round: {state.get("debate_rounds", 0)}/3

Score this outline on all 5 criteria and provide your verdict."""

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
        }],
    }

    if not validation["passed"]:
        updates["debate_rounds"] = current_rounds + 1
        updates["agent_notes"] = [AgentNote(
            agent_name="validator",
            note_type="critique",
            content=f"Score: {validation['score']}/50 — {validation['feedback']}",
        )]

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
    )
