"""
Story Miner Agent — empathetic interviewer that extracts story fragments.
No external tools. Pure conversational LLM.
"""
import uuid
from datetime import datetime
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from agents.state import ArcwrightState, StoryFragment, AgentNote


_SYSTEM_PROMPT = """You are the Story Mining Agent — an empathetic interviewer and story archaeologist.

Your mission: help users discover valuable stories from their everyday life moments.

Core rules:
1. Ask ONE question at a time — never multiple questions in the same message
2. Start broad ("Tell me about a moment recently..."), then drill into specifics
3. Listen for emotional moments and dig DEEPER into them
4. Focus on: sensory details, emotional turning points, specific characters, conflict
5. Extract story fragments: concrete moments with emotion, character, and context
6. Do NOT suggest or invent stories — draw them OUT of the user
7. Keep tone warm, curious, and conversational
8. After 2-3 solid fragments, signal readiness with: "[FRAGMENTS_READY]"

Question types to use:
- Contrast: "What was different about that day compared to usual?"
- Sensory: "What did you see/hear/feel in that moment?"
- Stakes: "What would have happened if you hadn't been there?"
- Emotion: "What was going through your mind right then?"

If validator gave critique (check notes), address it by re-interviewing from a new angle.
If user seems stuck, use: "What's one small moment from the past week that surprised you?"

After gathering fragments, extract them in this JSON format (internal, not shown to user):
[FRAGMENT]: {"text": "...", "emotion": "..."}"""


def story_miner_node(state: ArcwrightState, llm) -> dict:
    """
    Story Miner node — conducts interactive Q&A to extract story fragments.

    Reads:  messages, story_fragments, agent_notes, rag_context
    Writes: story_fragments (append), messages (append), interview_questions_asked (append)
    """
    from langgraph.types import interrupt
    
    agent = create_react_agent(
        model=llm,
        tools=[],
        prompt=_system_prompt_with_context(state),
    )

    # Pass full conversation history
    result = agent.invoke({"messages": state.get("messages", [])})

    last_message = None
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
            last_message = msg
            break

    if last_message is None:
        return {}

    response_text = last_message.content
    new_fragments = _parse_fragments(response_text)
    clean_response = _strip_fragment_tags(response_text)

    # Interrupt and wait for user input
    user_response = interrupt({
        "type": "interview_question",
        "question": clean_response
    })
    
    user_message = user_response.get("messages", [])[0] if isinstance(user_response, dict) and "messages" in user_response else {"role": "user", "content": str(user_response)}

    updates: dict = {
        "messages": [
            {"role": "assistant", "content": clean_response},
            user_message
        ],
    }

    if new_fragments:
        updates["story_fragments"] = new_fragments
        updates["agent_notes"] = [AgentNote(
            agent_name="story_miner",
            note_type="insight",
            content=f"Extracted {len(new_fragments)} new fragment(s)",
        )]

    # Track question asked
    updates["interview_questions_asked"] = [clean_response[:200]]

    return updates


def _system_prompt_with_context(state: ArcwrightState) -> str:
    """Inject context (RAG tips, validator critique) into system prompt."""
    prompt = _SYSTEM_PROMPT

    # Inject RAG questioning techniques if available
    rag = state.get("rag_context", [])
    if rag:
        prompt += f"\n\nStorytelling framework context:\n{rag[0].get('response', '')[:500]}"

    # Inject Validator critique if in debate mode
    critic_notes = [
        n for n in state.get("agent_notes", [])
        if n.get("agent_name") == "validator" and n.get("note_type") == "critique"
    ]
    if critic_notes:
        latest_critique = critic_notes[-1]["content"]
        prompt += f"\n\nValidator critique to address:\n{latest_critique}"
        prompt += "\n\nRe-interview the user from a fresh angle to address these weaknesses."

    return prompt


def _parse_fragments(text: str) -> list[StoryFragment]:
    """Extract [FRAGMENT] JSON tags from agent response."""
    import re, json
    fragments = []
    pattern = r"\[FRAGMENT\]:\s*(\{[^}]+\})"
    for match in re.finditer(pattern, text):
        try:
            data = json.loads(match.group(1))
            fragments.append(StoryFragment(
                id=str(uuid.uuid4()),
                text=data.get("text", ""),
                emotion=data.get("emotion"),
                timestamp=datetime.now().isoformat(),
            ))
        except (json.JSONDecodeError, KeyError):
            pass
    return fragments


def _strip_fragment_tags(text: str) -> str:
    """Remove internal [FRAGMENT] tags from user-facing response."""
    import re
    return re.sub(r"\[FRAGMENT\]:\s*\{[^}]+\}", "", text).strip()
