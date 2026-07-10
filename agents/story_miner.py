"""
story_miner.py — Story Miner Agent for Arcwright Storytelling AI.

A conversational, empathetic interviewer that guides users to surface
compelling personal stories through gentle, focused questioning.
Extracts structured StoryFragment dicts once enough material has been gathered.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.state import ArcwrightState, StoryFragment

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MODEL_NAME = "gpt-4o-mini"
MIN_ROUNDS_BEFORE_EXTRACT = 2   # At least 2 user answers before extracting


# ─── System prompts ───────────────────────────────────────────────────────────

INTERVIEWER_SYSTEM_PROMPT = """Kamu adalah Story Miner — pewawancara yang empatik dan penuh rasa ingin tahu.
Tugasmu adalah membantu orang menemukan cerita menarik tersembunyi dalam pengalaman sehari-hari mereka.

PRINSIP UTAMA:
1. Tanyakan SATU pertanyaan saja per giliran — tidak boleh lebih.
2. Dengarkan dengan empati; validasi perasaan user sebelum menggali lebih dalam.
3. Fokus pada momen spesifik, bukan narasi umum.
4. Gunakan bahasa Indonesia yang natural dan casual (bukan formal).
5. Jika user sudah berbagi detail yang kaya, gali lebih dalam dengan "kenapa" dan "kamu ngerasa apa".

PERTANYAAN PEMBUKA (pilih yang paling relevan dengan konteks):
- "Apa hal kecil yang terjadi hari ini yang bikin kamu mikir atau ngerasa sesuatu?"
- "Ada momen spesifik yang pengen kamu ceritain? Sekecil apapun."
- "Kapan terakhir kali kamu ngerasa surprise — entah senang, sedih, atau bingung?"

PERTANYAAN PENGGALIAN (setelah user mulai cerita):
- "Cerita lebih detail dong — kamu ngerasa apa waktu itu?"
- "Ada satu detail yang paling kamu inget dari momen itu?"
- "Menurut kamu, kenapa kejadian itu berkesan buat kamu?"
- "Gimana reaksi orang lain waktu itu?"
- "Kalau kamu harus ceritain ini ke teman dekat, kamu mulai dari mana?"

TANDA CERITA SIAP DIEKSTRAK:
- User udah cerita momen spesifik (bukan cuma "hari ini biasa aja")
- Ada emosi yang muncul (senang, sedih, heran, malu, bangga, dll.)
- Ada konflik kecil atau kejutan
- User sudah menjawab minimal 2 pertanyaan dengan substansi

Jika cerita sudah cukup kaya, akhiri dengan kalimat seperti:
"Oke, aku udah nangkep benang merahnya! Biar aku olah ceritamu dulu ya."
"""

EXTRACTION_SYSTEM_PROMPT = """Kamu adalah analis cerita. Berdasarkan percakapan yang diberikan,
ekstrak story fragments dalam format JSON array.

INSTRUKSI:
- Ekstrak 1-3 StoryFragment paling kuat dari percakapan.
- Setiap fragment harus berupa momen spesifik, bukan rangkuman umum.
- Field "text": narasi fragment dalam 1-3 kalimat, tulis ulang agar lebih kuat.
- Field "emotion": emosi dominan (satu kata: "bangga", "malu", "heran", "sedih", "senang", dll.) atau null.
- Field "theme": tema universal singkat (contoh: "ketidaksempurnaan sebagai kekuatan", "koneksi manusia") atau null.

HANYA return JSON array, tidak ada teks lain. Contoh:
[
  {
    "text": "Saat presentasi, mic-nya mati dan aku terpaksa teriak ke 200 orang.",
    "emotion": "malu",
    "theme": "improvisasi di momen kritis"
  }
]
"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_llm() -> ChatOpenAI:
    """Instantiate the ChatOpenAI model."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
    return ChatOpenAI(model=MODEL_NAME, temperature=0.7, api_key=api_key)


def _count_human_messages(state: ArcwrightState) -> int:
    """Count the number of HumanMessage turns in state messages."""
    messages = state.get("messages", [])
    return sum(1 for m in messages if isinstance(m, HumanMessage))


def _extract_story_fragments(
    llm: ChatOpenAI, state: ArcwrightState
) -> list[StoryFragment]:
    """Ask the LLM to parse story fragments from the conversation history.

    Args:
        llm: The ChatOpenAI instance.
        state: Current ArcwrightState with messages.

    Returns:
        A list of StoryFragment dicts (may be empty on failure).
    """
    messages = state.get("messages", [])
    # Build a readable transcript
    transcript_lines: list[str] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            transcript_lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            transcript_lines.append(f"Interviewer: {msg.content}")
    transcript = "\n".join(transcript_lines)

    try:
        extraction_response = llm.invoke(
            [
                SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=f"Percakapan:\n\n{transcript}"),
            ]
        )
        raw = extraction_response.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [
                StoryFragment(
                    text=item.get("text", ""),
                    emotion=item.get("emotion"),
                    theme=item.get("theme"),
                )
                for item in parsed
                if isinstance(item, dict) and item.get("text")
            ]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("[StoryMiner] Fragment extraction parse error: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("[StoryMiner] Fragment extraction failed: %s", exc, exc_info=True)

    return []


# ─── Node function ─────────────────────────────────────────────────────────────

def story_miner_node(state: ArcwrightState) -> dict[str, Any]:
    """LangGraph node: conduct empathetic interview and extract story fragments.

    On each invocation this node either:
    - Asks the user the next focused interview question, OR
    - Extracts StoryFragment dicts from the conversation (after ≥2 rounds).

    Args:
        state: The shared ArcwrightState dict passed by LangGraph.

    Returns:
        A partial-state dict with keys:
        - ``messages``: list containing the new AIMessage (appended via add_messages).
        - ``story_fragments``: list of StoryFragment dicts (may be empty early on).
        - ``interview_round``: incremented round counter.
    """
    logger.info("[StoryMiner] Node triggered — round %d.", state.get("interview_round", 0))

    try:
        llm = _get_llm()
        human_rounds = _count_human_messages(state)
        interview_round = state.get("interview_round", 0)
        current_messages = state.get("messages", [])

        # ── Decide: ask next question or extract ─────────────────────────────
        should_extract = human_rounds >= MIN_ROUNDS_BEFORE_EXTRACT

        if should_extract:
            logger.info("[StoryMiner] Sufficient rounds — extracting fragments.")
            fragments = _extract_story_fragments(llm, state)
        else:
            fragments = []

        # ── Generate next interviewer message ─────────────────────────────────
        prompt_messages: list[Any] = [SystemMessage(content=INTERVIEWER_SYSTEM_PROMPT)]
        prompt_messages.extend(current_messages)

        # Hint the model about extraction status
        if should_extract and fragments:
            prompt_messages.append(
                SystemMessage(
                    content=(
                        "Cerita sudah cukup kaya untuk diolah. "
                        "Sampaikan ke user bahwa kamu akan mengolah ceritanya, "
                        "lalu tutup sesi wawancara dengan hangat."
                    )
                )
            )
        elif should_extract and not fragments:
            prompt_messages.append(
                SystemMessage(
                    content=(
                        "Cerita belum cukup spesifik. "
                        "Tanyakan satu pertanyaan menggali yang meminta detail konkret."
                    )
                )
            )

        ai_response = llm.invoke(prompt_messages)
        ai_message = AIMessage(content=ai_response.content)

        logger.info("[StoryMiner] AI response generated. Fragments extracted: %d.", len(fragments))

        return {
            "messages": [ai_message],
            "story_fragments": fragments,
            "interview_round": interview_round + 1,
        }

    except EnvironmentError as exc:
        logger.error("[StoryMiner] Config error: %s", exc)
        fallback = AIMessage(
            content="Maaf, ada masalah konfigurasi. Silakan hubungi administrator."
        )
        return {
            "messages": [fallback],
            "story_fragments": [],
            "interview_round": state.get("interview_round", 0) + 1,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("[StoryMiner] Unexpected error: %s", exc, exc_info=True)
        fallback = AIMessage(
            content="Maaf, terjadi kesalahan. Coba lagi sebentar ya!"
        )
        return {
            "messages": [fallback],
            "story_fragments": [],
            "interview_round": state.get("interview_round", 0) + 1,
        }
