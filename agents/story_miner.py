"""
Story Miner Agent — empathetic interviewer that extracts story fragments.

Dua mode operasi:
  1. interview_mode (default): Generate pertanyaan → interrupt() → tunggu user
  2. targeted_probe_mode: Story Miner tau dari Validator area mana yang lemah,
     langsung tanya user hal yang spesifik itu, kemudian resume interview normal.

No external tools. Pure conversational LLM + robust fragment extraction.
"""
import uuid
import json
import re
from datetime import datetime
from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt

from agents.state import ArcwrightState, StoryFragment, AgentNote, ThoughtProcess


# ── System Prompt Base ────────────────────────────────────────────────────────

_SYSTEM_PROMPT_BASE = """You are Yui — the Story Mining Agent. An empathetic interviewer and story archaeologist.

Your mission: help users discover compelling stories hidden in their everyday life moments.

## Language Rules (IMPORTANT)
- Your PRIMARY language is English. Always respond in English.
- EXCEPTION: if the user writes in another language, naturally mirror their language for warmth,
  but frame story fragments and tags ([FRAGMENT], [FRAGMENTS_READY]) in English always.
- RAG context and storytelling frameworks are in English — apply them directly.

## Core Interview Rules
1. Ask ONE question at a time — never multiple questions in the same message
2. Start broad, then drill into SPECIFIC sensory details and emotional moments
3. Focus on: exact moments, specific characters, sensory details, emotional turning points
4. Do NOT suggest or invent stories — draw them OUT of the user
5. Keep tone warm, curious, and conversational — like a friend who genuinely cares
6. After 3 solid story fragments, signal readiness: [FRAGMENTS_READY]

## Question types to rotate through
- Opening: "Tell me — when was the last time you felt genuinely [emotion]?"
- Contrast: "What made that day different from a normal one?"
- Sensory: "Where were you exactly? What did it look like around you?"
- Stakes: "What would have happened if you hadn't been there?"
- Emotion: "What was going through your mind at that exact moment?"
- Character: "Who else was there? How did they react?"
- Before/After: "How did life feel different after that happened?"

## Fragment Extraction (internal — NOT shown to user)
When you identify a concrete story moment, extract it with:
[FRAGMENT]: {"text": "<the specific moment in 1-2 sentences>", "emotion": "<primary emotion>", "has_character": true/false, "has_sensory": true/false, "has_conflict": true/false}

Quality fragments must have:
- Specific detail (not vague)
- Emotional weight
- At least 2 of: character, sensory detail, conflict/tension"""


def _build_system_prompt(state: ArcwrightState) -> str:
    """Build contextual system prompt with RAG techniques and any validator feedback."""
    prompt = _SYSTEM_PROMPT_BASE

    # ── Language override from user_profile ───────────────────────────────
    lang = state.get("user_profile", {}).get("preferred_language", "en")
    user_name = state.get("user_profile", {}).get("name", "")
    if lang == "id":
        prompt += (
            "\n\n## Active Language Setting\n"
            "The user prefers Indonesian (Bahasa Indonesia). "
            "Respond primarily in Indonesian/Bahasa Indonesia. "
            "Keep story tags ([FRAGMENT], [FRAGMENTS_READY]) in English."
        )
    else:
        prompt += (
            "\n\n## Active Language Setting\n"
            "The user prefers English. Respond in English."
        )
    if user_name and user_name != "User":
        prompt += f"\nThe user's name is {user_name}. Address them by name occasionally."

    # ── Inject RAG context ─────────────────────────────────────────────────
    # Ambil semua RAG results yang relevan untuk mining
    rag_results = state.get("rag_results", [])
    mining_results = [r for r in rag_results if r.get("query_purpose") in ("mining_bootstrap", "mining_probe")]

    if mining_results:
        latest_rag = mining_results[-1]
        synthesis = latest_rag.get("synthesis", "")
        source_books = latest_rag.get("source_books", [])
        if synthesis:
            books_str = ", ".join(source_books) if source_books else "storytelling masters"
            prompt += f"\n\n## Storytelling Techniques (from {books_str}):\n{synthesis}"

    elif state.get("rag_context"):
        # Legacy fallback
        rag = state.get("rag_context", [])
        if rag:
            prompt += f"\n\n## Storytelling Framework Context:\n{rag[0].get('response', '')}"

    # ── Inject targeted probe context ──────────────────────────────────────
    if state.get("targeted_probe_mode"):
        # Cari critique terbaru dari validator
        critic_notes = [
            n for n in state.get("agent_notes", [])
            if n.get("agent_name") == "validator" and n.get("note_type") == "critique"
        ]
        validation = state.get("validation_result")

        if critic_notes or validation:
            prompt += "\n\n## ⚠️ TARGETED PROBE MODE"
            prompt += "\nThe story outline was rejected by the Story Validator. You need to gather MORE SPECIFIC information."

            if validation:
                weak_areas = validation.get("weak_areas", [])
                targeted_q = validation.get("targeted_question", "")
                if weak_areas:
                    prompt += f"\nWeak areas that need more material: {', '.join(weak_areas)}"
                if targeted_q:
                    prompt += f"\nSuggested targeted question: {targeted_q}"
                    prompt += "\nUse this as your starting point, then dig deeper."

            if critic_notes:
                latest = critic_notes[-1]["content"]
                prompt += f"\nValidator critique: {latest}"

            prompt += "\n\nAsk ONE targeted question that will get the specific detail needed to address the weakness."

    return prompt


def _score_fragment_quality(fragment_data: dict) -> int:
    """
    Score fragment quality 0-10.
    Threshold: ≥6 dihitung sebagai fragment berkualitas.
    """
    score = 0
    text = fragment_data.get("text", "")

    # Base score dari panjang dan spesifisitas teks
    if len(text) > 50:
        score += 2
    if len(text) > 100:
        score += 1

    # Structural markers
    if fragment_data.get("has_character"):
        score += 2
    if fragment_data.get("has_sensory"):
        score += 2
    if fragment_data.get("has_conflict"):
        score += 2

    # Emotional weight
    emotion = fragment_data.get("emotion", "")
    if emotion and emotion not in ("unknown", ""):
        score += 1

    return min(score, 10)


def _parse_fragments_v2(text: str, turn: int) -> list[StoryFragment]:
    """
    Robust fragment extraction: parses extended [FRAGMENT] format dengan quality scoring.
    """
    fragments = []

    # Pattern untuk format baru (dengan flags)
    pattern_full = r'\[FRAGMENT\]:\s*(\{[^}]+\})'
    for match in re.finditer(pattern_full, text):
        try:
            raw = match.group(1)
            data = json.loads(raw)
            quality = _score_fragment_quality(data)
            fragments.append(StoryFragment(
                id=str(uuid.uuid4()),
                text=data.get("text", ""),
                emotion=data.get("emotion"),
                timestamp=datetime.now().isoformat(),
                quality_score=quality,
                source_turn=turn,
            ))
        except (json.JSONDecodeError, KeyError):
            pass

    return fragments


def _llm_fallback_extract(user_text: str, llm, turn: int) -> list[StoryFragment]:
    """
    LLM fallback extraction: jika LLM lupa tag [FRAGMENT], minta extract langsung.
    Dipanggil hanya jika regex extraction menghasilkan 0 fragments.
    """
    if not user_text or len(user_text.strip()) < 30:
        return []

    prompt = f"""Extract a story fragment from this user message. Return ONLY JSON, no other text.

User message: "{user_text[:600]}"

Return this exact JSON (or null if no story moment found):
{{"text": "<the specific story moment in 1-2 sentences>", "emotion": "<primary emotion felt>", "has_character": <true/false>, "has_sensory": <true/false>, "has_conflict": <true/false>}}"""

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Clean up possible markdown
        content = re.sub(r"```json\s*|\s*```", "", content).strip()
        if content.lower() == "null" or not content.startswith("{"):
            return []

        data = json.loads(content)
        if not data.get("text"):
            return []

        quality = _score_fragment_quality(data)
        return [StoryFragment(
            id=str(uuid.uuid4()),
            text=data.get("text", ""),
            emotion=data.get("emotion"),
            timestamp=datetime.now().isoformat(),
            quality_score=quality,
            source_turn=turn,
        )]
    except Exception:
        return []


def _strip_fragment_tags(text: str) -> str:
    """Remove internal [FRAGMENT] tags and [FRAGMENTS_READY] from user-facing response."""
    cleaned = re.sub(r'\[FRAGMENT\]:\s*\{[^}]+\}', '', text)
    cleaned = cleaned.replace("[FRAGMENTS_READY]", "")
    return cleaned.strip()


def _count_quality_fragments(fragments: list) -> int:
    """Count fragments with quality_score >= QUALITY_THRESHOLD."""
    from config import settings
    return sum(1 for f in fragments if f.get("quality_score", 0) >= settings.FRAGMENT_QUALITY_THRESHOLD)


# ── Main Node ──────────────────────────────────────────────────────────────────

def story_miner_node(state: ArcwrightState, llm) -> dict:
    """
    Story Miner node — empathetic interviewer with two modes:
    
    - Normal mode: generate interview question → interrupt() → user answers
    - Targeted probe mode: Validator rejected outline, ask user specifically
      about the weak areas identified by Validator
    
    Reads:  messages, story_fragments, rag_results, targeted_probe_mode, validation_result
    Writes: messages (append), story_fragments (append), agent_notes, turn_count
    """
    messages = state.get("messages", [])
    fragments = state.get("story_fragments", [])
    turn_count = state.get("turn_count", 0)
    targeted = state.get("targeted_probe_mode", False)

    thought = ThoughtProcess(
        agent="story_miner",
        timestamp=datetime.now().isoformat(),
        thought=f"Turn {turn_count}. Mode: {'targeted_probe' if targeted else 'interview'}. "
                f"{len(fragments)} fragments collected ({_count_quality_fragments(fragments)} quality).",
        data={"turn": turn_count, "fragment_count": len(fragments), "targeted": targeted}
    )

    # Build context-aware system prompt
    system_prompt = _build_system_prompt(state)

    agent = create_react_agent(
        model=llm,
        tools=[],
        prompt=system_prompt,
    )

    # Invoke agent dengan full conversation history
    result = agent.invoke({"messages": messages})

    # Ambil respons AI terbaru
    last_message = None
    existing_ids = {m.id for m in messages if hasattr(m, "id")}
    for msg in reversed(result.get("messages", [])):
        if (hasattr(msg, "type") and msg.type == "ai" and msg.content
                and hasattr(msg, "id") and msg.id not in existing_ids):
            last_message = msg
            break
        elif (hasattr(msg, "type") and msg.type == "ai" and msg.content
              and not hasattr(msg, "id") and msg not in messages):
            last_message = msg
            break

    if last_message is None:
        return {"thought_process": [thought]}

    response_text = last_message.content
    clean_response = _strip_fragment_tags(response_text)

    # ── Fragment extraction ────────────────────────────────────────────────
    new_fragments = _parse_fragments_v2(response_text, turn_count)

    # ── Interrupt: show question to user ──────────────────────────────────
    user_response = interrupt({
        "type": "interview_question",
        "question": clean_response,
    })

    # Extract user message from resume payload
    if isinstance(user_response, dict) and "messages" in user_response:
        user_message = user_response["messages"][0]
        user_text = user_message.get("content", "") if isinstance(user_message, dict) else getattr(user_message, "content", "")
    else:
        user_text = str(user_response)
        user_message = {"role": "user", "content": user_text}

    # ── LLM fallback extraction dari jawaban USER ──────────────────────────
    # Ini jalankan SETELAH user menjawab — extract dari jawaban user langsung
    if not new_fragments and user_text and len(user_text.strip()) > 30:
        new_fragments = _llm_fallback_extract(user_text, llm, turn_count)
        if new_fragments:
            thought["thought"] += f" (LLM fallback extracted {len(new_fragments)} fragment from user reply)"

    # ── Build state updates ────────────────────────────────────────────────
    new_quality_count = _count_quality_fragments(new_fragments)
    thought["thought"] += f" Extracted {len(new_fragments)} new fragments ({new_quality_count} quality)."
    if new_fragments:
        thought["data"] = {"extracted": [f["text"][:100] for f in new_fragments]}

    updates: dict = {
        "messages": [user_message],
        "thought_process": [thought],
        "turn_count": turn_count + 1,
    }

    if new_fragments:
        updates["story_fragments"] = new_fragments
        updates["agent_notes"] = [AgentNote(
            agent_name="story_miner",
            note_type="insight",
            content=f"Turn {turn_count}: extracted {len(new_fragments)} fragment(s), "
                    f"{new_quality_count} high-quality.",
        )]

    updates["interview_questions_asked"] = [clean_response[:200]]

    # Reset targeted probe mode setelah selesai bertanya
    if targeted:
        updates["targeted_probe_mode"] = False

    return updates
