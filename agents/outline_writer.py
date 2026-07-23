"""
Outline Writer Agent — synthesizes all inputs into a structured story outline.
Applies storytelling frameworks from RAG context (full, not truncated).
"""
import re
import json
from datetime import datetime
from langgraph.prebuilt import create_react_agent

from agents.state import ArcwrightState, StoryOutline, ThoughtProcess


_SYSTEM_PROMPT = """You are the Outline Writer — a story architect and structure builder.

Your job: synthesize story fragments, research, and frameworks into a compelling narrative outline.

Use ALL available inputs:
- Story fragments (the raw material — prioritize HIGH quality ones)
- RAG storytelling frameworks (apply the specific framework retrieved)
- Deep dive analysis (especially "hidden_gold" and "universal" perspectives)
- Web research trends (ensure platform fit and audience relevance)
- Validator critique (if revising — fix the specific weak areas)

Output this EXACT JSON structure:
[OUTLINE]:
{
  "title": "<compelling, specific headline — not generic>",
  "hook": "<opening line that grabs attention in 1-2 sentences>",
  "setup": "<introduce the world, character, and context in 2-3 sentences>",
  "turning_point": "<the moment everything changes — be VERY specific>",
  "struggle": "<the internal/external conflict or obstacle — concrete details>",
  "resolution": "<how it resolves — surprising or satisfying>",
  "punchline": "<emotional or thematic payoff — the lasting impression>",
  "platform": "<youtube|tiktok|podcast|blog|general>",
  "estimated_duration": "<2 min|5 min|10 min|15 min|long-form>"
}

Rules:
- Title must be SPECIFIC and evocative — NOT "My Story About..."
- Hook must work as a standalone opening line
- Turning point must feel EARNED from the setup (use the specific moment from fragments)
- Apply the storytelling framework from RAG context explicitly"""


def outline_writer_node(state: ArcwrightState, llm) -> dict:
    """
    Outline Writer node — synthesizes all inputs into structured outline.

    Reads:  story_fragments, rag_results, web_research, deep_dive_analysis, agent_notes
    Writes: story_outline (overwrite), current_phase
    """
    agent = create_react_agent(
        model=llm,
        tools=[],
        prompt=_SYSTEM_PROMPT,
    )

    fragments = state.get("story_fragments", [])
    rag_results = state.get("rag_results", [])
    web = state.get("web_research", [])
    deep_dive = state.get("deep_dive_analysis", {})
    platform = state.get("user_profile", {}).get("platform_target", "general")

    # Prioritize quality fragments
    from config import settings
    quality_frags = [f for f in fragments if f.get("quality_score", 0) >= settings.FRAGMENT_QUALITY_THRESHOLD]
    all_frags = quality_frags if quality_frags else fragments

    # Get best RAG context: prefer outlining-purpose, fallback to enriching
    rag_synthesis = ""
    rag_books = []
    for purpose in ("outlining", "enriching", "mining_probe"):
        match = next((r for r in reversed(rag_results) if r.get("query_purpose") == purpose), None)
        if match:
            rag_synthesis = match.get("synthesis", "")
            rag_books = match.get("source_books", [])
            break
    if not rag_synthesis and state.get("rag_context"):
        rag_synthesis = state["rag_context"][0].get("response", "")

    # Check if this is a revision
    critic_notes = [
        n for n in state.get("agent_notes", [])
        if n.get("agent_name") == "validator" and n.get("note_type") == "critique"
    ]
    revision_context = ""
    if critic_notes:
        latest = critic_notes[-1]["content"]
        validation = state.get("validation_result", {})
        weak_areas = validation.get("weak_areas", []) if validation else []
        revision_context = (
            f"\n\n## ⚠️ REVISION MODE — Fix these specific issues:\n{latest}\n"
            f"Weak areas to strengthen: {', '.join(weak_areas) if weak_areas else 'see critique above'}\n"
            f"Make specific, targeted improvements to these areas."
        )

    thought = ThoughtProcess(
        agent="outline_writer",
        timestamp=datetime.now().isoformat(),
        thought=f"Writing outline. {len(all_frags)} quality fragments. "
                f"RAG: {', '.join(rag_books[:2]) if rag_books else 'generic'}. "
                f"Revision: {'yes' if revision_context else 'no'}.",
        data={"fragment_count": len(all_frags), "is_revision": bool(revision_context)}
    )

    query = f"""Create a story outline from these inputs:

## STORY FRAGMENTS (quality-ranked):
{chr(10).join(f"- [Q:{f.get('quality_score',0)}/10] {f['text']} (emotion: {f.get('emotion','unknown')})" for f in all_frags[:8])}

## STORYTELLING FRAMEWORK (from {', '.join(rag_books) if rag_books else 'knowledge base'}):
{rag_synthesis if rag_synthesis else "No specific framework — use best practices"}

## DEEP DIVE ANALYSIS:
- Surface: {deep_dive.get("surface", "N/A")}
- Psychological: {deep_dive.get("psychological", "N/A")}
- Universal theme: {deep_dive.get("universal", "N/A")}
- Opposing view: {deep_dive.get("opposing", "N/A")}
- Hidden gold: {deep_dive.get("hidden_gold", "N/A")}

## AUDIENCE & PLATFORM:
Target platform: {platform}
Trends: {", ".join(str(t) for t in web[0].get("trends", [])[:3]) if web else "No trend data"}
Platform tips: {web[0].get("platform_tips", "") if web else ""}
{revision_context}

Build the most compelling outline possible. Apply the storytelling framework explicitly. Output ONLY the [OUTLINE] JSON block. Do NOT write any conversational text, greetings, or instructions to check the UI panel."""

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    response_text = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
            response_text = msg.content
            break

    outline = _parse_outline(response_text, platform)
    return {
        "story_outline": outline,
        "validation_result": None,
        "current_phase": "validating",
        "thought_process": [thought],
    }


def _parse_outline(text: str, platform: str) -> StoryOutline:
    """Parse [OUTLINE] JSON from agent response."""
    pattern = r"\[OUTLINE\]:\s*(\{[\s\S]+?\})\s*(?:\n|$)"
    match = re.search(pattern, text)

    if match:
        try:
            data = json.loads(match.group(1))
            return StoryOutline(
                title=data.get("title", "Untitled"),
                hook=data.get("hook", ""),
                setup=data.get("setup", ""),
                turning_point=data.get("turning_point", ""),
                struggle=data.get("struggle", ""),
                resolution=data.get("resolution", ""),
                punchline=data.get("punchline", ""),
                platform=data.get("platform", platform),
                estimated_duration=data.get("estimated_duration", "5 min"),
            )
        except (json.JSONDecodeError, KeyError):
            pass

    return StoryOutline(
        title="Story Outline",
        hook=text[:200],
        setup="",
        turning_point="",
        struggle="",
        resolution="",
        punchline="",
        platform=platform,
        estimated_duration="5 min",
    )
