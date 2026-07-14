"""
Deep Dive Agent — analyzes story from 5 distinct perspectives.
Runs in parallel with Web Researcher via Send().
"""
from langgraph.prebuilt import create_react_agent

from agents.state import ArcwrightState


_SYSTEM_PROMPT = """You are the Deep Dive Agent — a multi-perspective story analyst.

Your job: analyze the story material from 5 distinct perspectives to uncover hidden angles.

Given the story fragments, produce this EXACT JSON structure:

{
  "surface": "What is literally happening? The concrete facts of the story.",
  "psychological": "What emotions and motivations are driving the characters? What internal conflict exists?",
  "universal": "What bigger human truth does this story reveal? What universal experience does it tap into?",
  "opposing": "How could someone see this situation completely differently? What's the other side?",
  "hidden_gold": "What unexpected angle, irony, or insight hasn't been explored yet? The twist nobody sees coming."
}

Rules:
- Each perspective MUST be distinct and add new value
- Be specific to THIS story — no generic observations
- "hidden_gold" should be genuinely surprising
- Keep each field to 2-3 sentences max

Output ONLY the JSON. No preamble, no explanation."""


def deep_dive_node(state: ArcwrightState, llm) -> dict:
    """
    Deep Dive node — multi-perspective analysis of story material.

    Reads:  story_fragments, rag_context
    Writes: deep_dive_analysis (overwrite)
    """
    agent = create_react_agent(
        model=llm,
        tools=[],
        state_modifier=_SYSTEM_PROMPT,
    )

    fragments = state.get("story_fragments", [])
    rag = state.get("rag_context", [])

    fragments_text = "\n".join(f"- {f['text']}" for f in fragments)
    rag_context = rag[0].get("response", "")[:400] if rag else ""

    query = f"""Analyze these story fragments from 5 perspectives:

Story fragments:
{fragments_text}

{f"Storytelling context: {rag_context}" if rag_context else ""}

Produce the 5-perspective JSON analysis."""

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    response_text = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
            response_text = msg.content
            break

    analysis = _parse_analysis(response_text)
    return {"deep_dive_analysis": analysis}


def _parse_analysis(text: str) -> dict:
    """Parse 5-perspective JSON from agent response."""
    import re, json

    # Try to extract JSON block
    json_match = re.search(r"\{[\s\S]+\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            required = {"surface", "psychological", "universal", "opposing", "hidden_gold"}
            if required.issubset(data.keys()):
                return data
        except json.JSONDecodeError:
            pass

    # Fallback: return raw as hidden_gold
    return {
        "surface": "",
        "psychological": "",
        "universal": "",
        "opposing": "",
        "hidden_gold": text[:500],
        "_parse_error": True,
    }
