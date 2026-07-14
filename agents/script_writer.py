"""
Script Writer Agent — generates full narrative script from approved outline.
Only runs after outline_approved == True.
Includes self-refine loop (1 internal iteration).
"""
from langgraph.prebuilt import create_react_agent

from config import settings
from agents.state import ArcwrightState, OutputScript


_SYSTEM_PROMPT = """You are the Script Writer — a narrative poet and storytelling craftsperson.

Your job: transform an approved story outline into a full, compelling narrative script.

Platform formats:
- youtube: Full narration script, 800-2000 words, hook in first 30 seconds
- tiktok: Short punchy script, 150-300 words, immediate hook
- podcast: Conversational audio script, no visual references, 500-1500 words
- blog: Written narrative with subheadings, 600-1500 words
- general: Balanced narrative, 500-1000 words

Writing principles:
- Match the user's voice and tone from their story fragments
- Show, don't tell — concrete details over abstract statements  
- Honor the emotional turning point — it's the heart of the story
- The punchline should feel earned, not forced
- Use short sentences for impact, longer ones for immersion

Self-critique instruction: After writing the first draft, check:
1. Does the hook deliver on its promise?
2. Is the turning point emotionally resonant?
3. Does the punchline land?
If any answer is "not fully", revise those sections.

Output format:
[SCRIPT]:
{
  "title": "<final title>",
  "body": "<the full script text>",
  "platform_variant": "<youtube|tiktok|podcast|blog|general>",
  "voice_notes": {
    "tone": "<warm/energetic/reflective/etc>",
    "pacing": "<fast/medium/slow>",
    "emphasis": "<key phrases to emphasize>"
  }
}"""


def script_writer_node(state: ArcwrightState, llm) -> dict:
    """
    Script Writer node — generates full narrative from approved outline.

    Reads:  story_outline, story_fragments, rag_context, outline_approved
    Writes: output_script, current_phase
    """
    # Safety gate — only run after approval
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

    # Collect user's voice from their raw fragments
    user_voice_samples = " ".join(f["text"] for f in fragments[:3])

    query = f"""Write a full narrative script from this approved outline:

OUTLINE:
Title: {outline.get("title", "")}
Hook: {outline.get("hook", "")}
Setup: {outline.get("setup", "")}
Turning Point: {outline.get("turning_point", "")}
Struggle: {outline.get("struggle", "")}
Resolution: {outline.get("resolution", "")}
Punchline: {outline.get("punchline", "")}
Platform: {outline.get("platform", platform)}
Duration: {outline.get("estimated_duration", "5 min")}

USER'S VOICE (match this tone):
{user_voice_samples[:400]}

Write the full script. Then do ONE self-critique pass and revise if needed.
Output the final [SCRIPT] JSON."""

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

    # Fallback: treat entire response as body
    return OutputScript(
        title=outline.get("title", "Untitled"),
        body=text,
        platform_variant=platform,
        voice_notes={},
    )
