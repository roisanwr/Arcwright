"""
Web Researcher Agent — searches real-time trends for audience intelligence.
Uses Tavily. Gracefully skips if TAVILY_API_KEY is not set.
Runs in parallel with Deep Dive via Send().
"""
from langgraph.prebuilt import create_react_agent

from config import settings
from agents.state import ArcwrightState


_SYSTEM_PROMPT = """You are the Web Research Agent — a trend scout and audience intelligence gatherer.

Your job: find real-time information about what's resonating with audiences right now.

For the given story themes, research:
1. Current trends on the target platform (YouTube/TikTok/Podcast/Blog)
2. Related stories or topics that are resonating with audiences
3. Audience demographics and what they care about
4. Similar successful content angles in the past 3-6 months

Output format — always end with this JSON block:
[WEB_RESEARCH]:
{
  "trends": ["trend 1", "trend 2"],
  "audience_insights": "what this audience cares about",
  "platform_tips": "specific format/length/style tips for the target platform",
  "related_content": "examples of successful similar content"
}"""


def web_researcher_node(state: ArcwrightState, llm) -> dict:
    """
    Web Researcher node — finds real-time trends for story angle.

    Reads:  story_fragments, user_profile
    Writes: web_research (overwrite)
    """
    if not settings.TAVILY_API_KEY:
        # Gracefully skip if no API key
        return {
            "web_research": [{
                "note": "Web research skipped — TAVILY_API_KEY not set",
                "trends": [],
                "audience_insights": "",
                "platform_tips": "",
            }]
        }

    from langchain_community.tools.tavily_search import TavilySearchResults
    import os
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY

    tavily_tool = TavilySearchResults(max_results=5)
    agent = create_react_agent(
        model=llm,
        tools=[tavily_tool],
        prompt=_SYSTEM_PROMPT,
    )

    # Build search context from fragments
    fragments = state.get("story_fragments", [])
    platform = state.get("user_profile", {}).get("platform_target", "general")
    themes = " ".join(f["text"][:100] for f in fragments[:3])

    query = (
        f"What storytelling trends are popular on {platform} in 2025 related to: {themes}. "
        f"What makes content resonate with this audience?"
    )

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    response_text = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
            response_text = msg.content
            break

    web_data = _parse_web_research(response_text)
    return {"web_research": [web_data]}


def _parse_web_research(text: str) -> dict:
    """Extract [WEB_RESEARCH] JSON from agent response."""
    import re, json
    pattern = r"\[WEB_RESEARCH\]:\s*(\{[\s\S]+?\})\s*$"
    match = re.search(pattern, text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Fallback: return raw text
    return {
        "raw": text,
        "trends": [],
        "audience_insights": text[:500],
        "platform_tips": "",
    }
