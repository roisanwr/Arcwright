"""
Deep Dive Agent — analyzes story from 5 distinct perspectives.
Runs in parallel with Web Researcher via Send().
Now also consults RAG for enriching-phase framework context.
"""
from datetime import datetime
from langgraph.prebuilt import create_react_agent

from agents.state import ArcwrightState, ThoughtProcess


_SYSTEM_PROMPT = """You are the Deep Dive Agent — a multi-perspective story analyst.

Your job: analyze the story material from 5 distinct perspectives to uncover hidden angles.

Given the story fragments and storytelling framework context, produce this EXACT JSON structure:

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
- "hidden_gold" should be genuinely surprising and actionable for storytelling
- Keep each field to 2-3 sentences max
- Reference the storytelling framework context when relevant

Output ONLY the JSON. No preamble, no explanation."""


def deep_dive_node(state: ArcwrightState, llm) -> dict:
    """
    Deep Dive node — multi-perspective analysis of story material.
    Now uses full RAG synthesis context (not truncated).

    Reads:  story_fragments, rag_results, rag_context
    Writes: deep_dive_analysis (overwrite)
    """
    agent = create_react_agent(
        model=llm,
        tools=[],
        prompt=_SYSTEM_PROMPT,
    )

    fragments = state.get("story_fragments", [])
    rag_results = state.get("rag_results", [])

    # Get best RAG context for enriching
    from config import settings
    enriching_rag = next(
        (r for r in reversed(rag_results) if r.get("query_purpose") in ("enriching", "mining_probe")), None
    )
    rag_synthesis = ""
    rag_books = []
    if enriching_rag:
        rag_synthesis = enriching_rag.get("synthesis", "")
        rag_books = enriching_rag.get("source_books", [])
    elif state.get("rag_context"):
        rag_synthesis = state["rag_context"][0].get("response", "")

    # Prioritize quality fragments
    quality_frags = [f for f in fragments if f.get("quality_score", 0) >= settings.FRAGMENT_QUALITY_THRESHOLD]
    analysis_frags = quality_frags if quality_frags else fragments

    thought = ThoughtProcess(
        agent="deep_dive",
        timestamp=datetime.now().isoformat(),
        thought=f"Analyzing {len(analysis_frags)} fragments from 5 perspectives. "
                f"RAG books: {', '.join(rag_books[:2]) if rag_books else 'none'}.",
        data={"fragment_count": len(analysis_frags), "has_rag": bool(rag_synthesis)}
    )

    fragments_text = "\n".join(f"- {f['text']} (emotion: {f.get('emotion', 'unknown')})" for f in analysis_frags)

    query = f"""Analyze these story fragments from 5 perspectives:

## Story Fragments:
{fragments_text}

## Storytelling Framework Context (from {', '.join(rag_books) if rag_books else 'knowledge base'}):
{rag_synthesis if rag_synthesis else "No specific framework context available."}

Produce the 5-perspective JSON analysis. Be specific to THIS story."""

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    response_text = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
            response_text = msg.content
            break

    analysis = _parse_analysis(response_text)
    return {
        "deep_dive_analysis": analysis,
        "thought_process": [thought],
    }


def _parse_analysis(text: str) -> dict:
    """Parse 5-perspective JSON from agent response."""
    import re, json

    json_match = re.search(r"\{[\s\S]+\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            required = {"surface", "psychological", "universal", "opposing", "hidden_gold"}
            if required.issubset(data.keys()):
                return data
        except json.JSONDecodeError:
            pass

    return {
        "surface": "",
        "psychological": "",
        "universal": "",
        "opposing": "",
        "hidden_gold": text[:500],
        "_parse_error": True,
    }
