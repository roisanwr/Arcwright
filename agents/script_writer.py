"""
Script Writer Agent — generates full narrative script from approved outline.
Only runs after outline_approved == True.
Now includes RAG-informed writing techniques (platform-specific).
Includes self-refine loop (1 internal iteration).
"""
from datetime import datetime
from langgraph.prebuilt import create_react_agent

from config import settings
from agents.state import ArcwrightState, OutputScript, ThoughtProcess


_SYSTEM_PROMPT = """You are the Script Writer — a narrative poet and storytelling craftsperson.

Your job: transform an approved story outline into a full, compelling narrative script.

Platform formats:
- youtube: Full narration script, 800-2000 words, hook in first 30 seconds
- tiktok: Short punchy script, 150-300 words, immediate hook, fast pacing
- podcast: Conversational audio script, no visual references, 500-1500 words
- blog: Written narrative with subheadings, 600-1500 words
- general: Balanced narrative, 500-1000 words

Writing principles:
- Match the user's voice and tone from their story fragments
- Show, don't tell — concrete details over abstract statements
- Honor the emotional turning point — it's the heart of the story
- The punchline should feel earned, not forced
- Apply the writing techniques from the RAG context

Self-critique instruction: After writing the first draft, check:
1. Does the hook deliver on its promise?
2. Is the turning point emotionally resonant and specific?
3. Does the punchline land with emotional truth?
If any answer is "not fully", revise those sections before outputting.

Output format:
[SCRIPT]:
{
  "title": "<final title>",
  "body": "<the full script text>",
  "platform_variant": "<youtube|tiktok|podcast|blog|general>",
  "voice_notes": {
    "tone": "<warm/energetic/reflective/etc>",
    "pacing": "<fast/medium/slow>",
    "emphasis": "<key phrases to emphasize when reading>"
  }
}"""


def script_writer_node(state: ArcwrightState, llm) -> dict:
    """
    Script Writer node — generates full narrative from approved outline.
    Consults RAG for platform-specific writing techniques.

    Reads:  story_outline, story_fragments, rag_results, outline_approved
    Writes: output_script, current_phase
    """
    if not state.get("outline_approved"):
        return {}

    agent = create_react_agent(
        model=llm,
        tools=[],
        prompt=_SYSTEM_PROMPT,
    )

    outline = state.get("story_outline", {})
    fragments = state.get("story_fragments", [])
    platform = state.get("user_profile", {}).get("platform_target", "general")

    # Get scripting RAG context (specific writing techniques)
    rag_results = state.get("rag_results", [])
    scripting_rag = next(
        (r for r in reversed(rag_results) if r.get("query_purpose") == "scripting"), None
    )
    # Fallback to enriching or latest
    if not scripting_rag:
        scripting_rag = next(
            (r for r in reversed(rag_results) if r.get("query_purpose") in ("enriching", "outlining")), None
        )
    scripting_synthesis = scripting_rag.get("synthesis", "") if scripting_rag else ""
    scripting_books = scripting_rag.get("source_books", []) if scripting_rag else []

    # Collect user's voice from their raw fragments (prefer quality ones)
    quality_frags = [f for f in fragments if f.get("quality_score", 0) >= settings.FRAGMENT_QUALITY_THRESHOLD]
    voice_frags = quality_frags[:3] if quality_frags else fragments[:3]
    user_voice_samples = " ".join(f["text"] for f in voice_frags)

    thought = ThoughtProcess(
        agent="script_writer",
        timestamp=datetime.now().isoformat(),
        thought=f"Writing {platform} script for '{outline.get('title', '')}'. "
                f"RAG books: {', '.join(scripting_books[:2]) if scripting_books else 'none'}. "
                f"{len(quality_frags)} quality fragments for voice matching.",
        data={"platform": platform, "has_scripting_rag": bool(scripting_synthesis)}
    )

    query = f"""Write a full narrative script from this approved outline:

## OUTLINE:
Title: {outline.get("title", "")}
Hook: {outline.get("hook", "")}
Setup: {outline.get("setup", "")}
Turning Point: {outline.get("turning_point", "")}
Struggle: {outline.get("struggle", "")}
Resolution: {outline.get("resolution", "")}
Punchline: {outline.get("punchline", "")}
Platform: {outline.get("platform", platform)}
Duration: {outline.get("estimated_duration", "5 min")}

## USER'S VOICE (match this tone and language style):
{user_voice_samples[:500]}

## WRITING TECHNIQUES (from {', '.join(scripting_books) if scripting_books else 'storytelling masters'}):
{scripting_synthesis if scripting_synthesis else "Apply best practices for " + platform + " storytelling"}

Write the full script. Then do ONE self-critique pass and revise if needed.
IMPORTANT: Output ONLY the [SCRIPT] JSON block. Do NOT write any greetings, conversational text, or closing remarks instructing the user to check UI panels. Only the JSON block is allowed."""

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    response_text = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
            response_text = msg.content
            break

    script = _parse_script(response_text, outline, platform)
    return {
        "output_script": script,
        "current_phase": "complete",
        "thought_process": [thought],
    }


def _parse_script(text: str, outline: dict, platform: str) -> OutputScript:
    """Parse [SCRIPT] JSON from agent response."""
    import re, json

    pattern = r"\[SCRIPT\]:\s*(\{[\s\S]+\})\s*$"
    match = re.search(pattern, text)

    if match:
        try:
            data = json.loads(match.group(1))
            return OutputScript(
                title=data.get("title", outline.get("title", "Untitled")),
                body=data.get("body", ""),
                platform_variant=data.get("platform_variant", platform),
                voice_notes=data.get("voice_notes", {}),
            )
        except (json.JSONDecodeError, KeyError):
            pass

    return OutputScript(
        title=outline.get("title", "Untitled"),
        body=text,
        platform_variant=platform,
        voice_notes={},
    )
