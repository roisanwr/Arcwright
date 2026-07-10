"""
web_researcher.py — Web Researcher Agent for Arcwright Storytelling AI.

Performs targeted DuckDuckGo searches to surface current storytelling trends,
viral narrative patterns, and cultural context relevant to the user's story.
Capped at 2 searches per invocation to keep latency low.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_community.tools import DuckDuckGoSearchRun

from agents.state import AgentNote, ArcwrightState

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_SEARCHES = 2
SEARCH_RESULT_MAX_CHARS = 600   # Trim per-result to keep state lean


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_search_queries(state: ArcwrightState) -> list[str]:
    """Derive up to MAX_SEARCHES focused search queries from story fragments.

    Strategy:
    - Query 1: theme/emotion-based trend search (what's resonating on social media).
    - Query 2: narrative technique search grounded in the story's core event.

    Args:
        state: Current ArcwrightState with story_fragments.

    Returns:
        A list of 1–2 query strings.
    """
    fragments = state.get("story_fragments", [])
    platform = state.get("platform_target", "general")

    # Collect themes and emotions
    themes: list[str] = [f["theme"] for f in fragments if f.get("theme")]
    emotions: list[str] = [f["emotion"] for f in fragments if f.get("emotion")]
    texts: list[str] = [f["text"] for f in fragments if f.get("text")]

    queries: list[str] = []

    # ── Query 1: trend / social resonance ────────────────────────────────────
    if themes:
        theme_str = themes[0]
        emotion_str = emotions[0] if emotions else "relatable"
        platform_hint = f" {platform}" if platform != "general" else ""
        queries.append(
            f'storytelling trend "{theme_str}" {emotion_str}{platform_hint} 2024 2025'
        )
    elif emotions:
        queries.append(
            f"viral storytelling {emotions[0]} personal story trend {platform} 2025"
        )
    else:
        queries.append("viral personal storytelling techniques 2025 social media")

    # ── Query 2: narrative technique grounded in the story ────────────────────
    if texts and len(queries) < MAX_SEARCHES:
        # Extract a short excerpt (first 60 chars) as anchor
        excerpt = texts[0][:60].strip()
        queries.append(
            f'storytelling technique narrative hook "{excerpt[:40]}" audience connection'
        )
    elif len(queries) < MAX_SEARCHES:
        queries.append("how to make personal stories relatable storytelling craft")

    return queries[:MAX_SEARCHES]


def _run_search(tool: DuckDuckGoSearchRun, query: str) -> str:
    """Execute a single DuckDuckGo search with error handling.

    Args:
        tool: The DuckDuckGoSearchRun instance.
        query: The search query string.

    Returns:
        Search result string, or an error message on failure.
    """
    try:
        result = tool.run(query)
        # Trim to keep state lean
        if len(result) > SEARCH_RESULT_MAX_CHARS:
            result = result[:SEARCH_RESULT_MAX_CHARS] + "… [trimmed]"
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("[WebResearcher] Search failed for query '%s': %s", query, exc)
        return f"[Search unavailable: {type(exc).__name__}]"


# ─── Node function ─────────────────────────────────────────────────────────────

def web_researcher_node(state: ArcwrightState) -> dict[str, Any]:
    """LangGraph node: search the web for storytelling trends and context.

    Builds up to 2 targeted queries from ``story_fragments`` and executes them
    with DuckDuckGo (no API key required). Search failures are caught and
    reported gracefully so the pipeline can continue.

    Args:
        state: The shared ArcwrightState dict passed by LangGraph.

    Returns:
        A partial-state dict with keys:
        - ``web_research``: list of dicts with keys ``query`` and ``result``.
        - ``agent_notes``: list containing one AgentNote from this agent.
    """
    logger.info("[WebResearcher] Node triggered.")

    fragments = state.get("story_fragments", [])
    if not fragments:
        logger.warning("[WebResearcher] No story fragments available — skipping search.")
        return {
            "web_research": [],
            "agent_notes": [
                AgentNote(
                    agent="web_researcher",
                    note_type="flag",
                    content="Skipped web search: no story fragments available in state.",
                )
            ],
        }

    try:
        search_tool = DuckDuckGoSearchRun()
        queries = _build_search_queries(state)

        web_research: list[dict[str, str]] = []
        for query in queries:
            logger.info("[WebResearcher] Searching: %s", query)
            result = _run_search(search_tool, query)
            web_research.append({"query": query, "result": result})

        successful = sum(
            1 for r in web_research if not r["result"].startswith("[Search unavailable")
        )
        note_content = (
            f"Ran {len(web_research)} search(es), {successful} successful. "
            f"Queries: {'; '.join(q['query'][:60] for q in web_research)}"
        )

        logger.info("[WebResearcher] Completed — %d/%d searches ok.", successful, len(web_research))

        return {
            "web_research": web_research,
            "agent_notes": [
                AgentNote(
                    agent="web_researcher",
                    note_type="insight",
                    content=note_content,
                )
            ],
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("[WebResearcher] Unexpected error: %s", exc, exc_info=True)
        return {
            "web_research": [],
            "agent_notes": [
                AgentNote(
                    agent="web_researcher",
                    note_type="flag",
                    content=f"Web research failed: {type(exc).__name__}: {exc}",
                )
            ],
        }
