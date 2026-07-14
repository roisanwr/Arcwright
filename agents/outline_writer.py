"""
Outline Writer Agent — synthesizes all inputs into a structured story outline.
Applies storytelling frameworks from RAG context.
"""
import re
import json
from langgraph.prebuilt import create_react_agent

from agents.state import ArcwrightState, StoryOutline


_SYSTEM_PROMPT = """You are the Outline Writer — a story architect and structure builder.

Your job: synthesize story fragments, research, and frameworks into a compelling narrative outline.

Use ALL available inputs:
- Story fragments (the raw material)
- RAG storytelling frameworks (apply the most relevant one)
- Deep dive analysis (especially "hidden_gold" and "universal" perspectives)
- Web research trends (ensure platform fit and audience relevance)

Output this EXACT JSON structure:
[OUTLINE]:
{
  "title": "<compelling, specific headline — not generic>",
  "hook": "<opening line that grabs attention in 1-2 sentences>",
  "setup": "<introduce the world, character, and context in 2-3 sentences>",
  "turning_point": "<the moment everything changes — be specific>",
  "struggle": "<the internal/external conflict or obstacle — concrete details>",
  "resolution": "<how it resolves — surprising or satisfying>",
  "punchline": "<emotional or thematic payoff — the lasting impression>",
  "platform": "<youtube|tiktok|podcast|blog|general>",
  "estimated_duration": "<2 min|5 min|10 min|15 min|long-form>"
}

Rules:
- Title must be specific and evocative — NOT "My Story About..."
- Hook must work as a standalone opening line
- Each field must build on the previous one
- Turning point must feel earned from the setup
- Use the storytelling framework from RAG context"""


def outline_writer_node(state: ArcwrightState, llm) -> dict:
    """
    Outline Writer node — synthesizes all inputs into structured outline.

    Reads:  story_fragments, rag_context, web_research, deep_dive_analysis
    Writes: story_outline (overwrite), current_phase
    """
    agent = create_react_agent(
        model=llm,
        tools=[],
        state_modifier=_SYSTEM_PROMPT,
    )

    fragments = state.get("story_fragments", [])
    rag = state.get("rag_context", [])
    web = state.get("web_research", [])
    deep_dive = state.get("deep_dive_analysis", {})
    platform = state.get("user_profile", {}).get("platform_target", "general")

    # Check if this is a revision (validator critique exists)
    critic_notes = [
        n for n in state.get("agent_notes", [])
        if n.get("agent_name") == "validator" and n.get("note_type") == "critique"
    ]
    revision_context = (
        f"\n\nPREVIOUS VALIDATOR CRITIQUE (fix these issues):\n{critic_notes[-1]['content']}"
        if critic_notes else ""
    )

    query = f"""Create a story outline from these inputs:

STORY FRAGMENTS:
{chr(10).join(f"- {f['text']} (emotion: {f.get('emotion', 'unknown')})" for f in fragments)}

STORYTELLING FRAMEWORK (from RAG):
{rag[0].get("response", "No framework available")[:600] if rag else "No RAG context"}

DEEP DIVE ANALYSIS:
- Surface: {deep_dive.get("surface", "")}
- Psychological: {deep_dive.get("psychological", "")}
- Universal theme: {deep_dive.get("universal", "")}
- Hidden gold: {deep_dive.get("hidden_gold", "")}

AUDIENCE & PLATFORM:
Target platform: {platform}
Trends: {", ".join(str(t) for t in web[0].get("trends", [])[:3]) if web else "No trend data"}
Platform tips: {web[0].get("platform_tips", "") if web else ""}
{revision_context}

Build the most compelling outline possible. Output the JSON."""

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    response_text = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
            response_text = msg.content
            break

    outline = _parse_outline(response_text, platform)
    return {
        "story_outline": outline,
        "current_phase": "validating",
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

    # Fallback outline from raw text
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
