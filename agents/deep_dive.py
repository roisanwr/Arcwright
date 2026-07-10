"""
deep_dive.py — Deep Dive Analysis Agent for Arcwright Storytelling AI.

Performs a structured multi-perspective analysis of the user's story fragments,
enriched with RAG context. Produces five analytical lenses — Surface,
Psychological, Universal Theme, Opposing View, and Hidden Gold — that give
downstream agents rich material to craft compelling narratives.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.state import AgentNote, ArcwrightState

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MODEL_NAME = "gpt-4o-mini"

ANALYSIS_PERSPECTIVES = [
    "surface",
    "psychological",
    "universal_theme",
    "opposing_view",
    "hidden_gold",
]

# ─── System prompt ────────────────────────────────────────────────────────────

DEEP_DIVE_SYSTEM_PROMPT = """Kamu adalah analis cerita profesional dengan keahlian dalam psikologi naratif,
storytelling lintas budaya, dan ilmu persuasi.

Tugasmu adalah menganalisis story fragments yang diberikan dari 5 perspektif berbeda.
Gunakan juga rag_context (kutipan buku storytelling) sebagai referensi teknik bila relevan.

FORMAT OUTPUT — kembalikan HANYA JSON object dengan 5 key berikut:

{
  "surface": "Apa yang terjadi secara literal — fakta, urutan kejadian, siapa melakukan apa.",
  "psychological": "Emosi, motivasi tersembunyi, kebutuhan psikologis yang terlibat. Mengapa orang bereaksi seperti itu?",
  "universal_theme": "Tema universal apa yang membuat cerita ini relevan bagi banyak orang? Hubungkan dengan pengalaman manusia yang lebih luas.",
  "opposing_view": "Bagaimana orang lain (dengan perspektif berbeda) mungkin melihat situasi yang sama secara berbeda? Sudut pandang antagonis atau alternatif.",
  "hidden_gold": "Detail paling kuat, mengejutkan, atau emosional yang harus ditonjolkan. Ini adalah 'bintang' dari cerita ini."
}

PANDUAN KUALITAS:
- Setiap perspektif: 2-4 kalimat yang konkret dan spesifik, BUKAN generik.
- hidden_gold harus menyebut detail spesifik dari cerita, bukan pernyataan umum.
- Gunakan bahasa Indonesia yang hidup dan evocative.
- Jika rag_context tersedia, integrasikan insight dari buku storytelling secara natural.
- HANYA return JSON — tidak ada teks, komentar, atau markdown di luar JSON.
"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_llm() -> ChatOpenAI:
    """Instantiate the ChatOpenAI model for deep dive analysis."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
    return ChatOpenAI(model=MODEL_NAME, temperature=0.4, api_key=api_key)


def _format_fragments(state: ArcwrightState) -> str:
    """Serialize story_fragments into a readable block for the prompt.

    Args:
        state: Current ArcwrightState.

    Returns:
        A formatted string representation of all story fragments.
    """
    fragments = state.get("story_fragments", [])
    if not fragments:
        return "(Tidak ada story fragment tersedia.)"

    lines: list[str] = []
    for i, frag in enumerate(fragments, start=1):
        lines.append(f"Fragment {i}:")
        lines.append(f"  Teks    : {frag.get('text', '')}")
        if frag.get("emotion"):
            lines.append(f"  Emosi   : {frag['emotion']}")
        if frag.get("theme"):
            lines.append(f"  Tema    : {frag['theme']}")
    return "\n".join(lines)


def _format_rag_context(state: ArcwrightState) -> str:
    """Serialize rag_context into a concise reference block.

    Args:
        state: Current ArcwrightState.

    Returns:
        A formatted string of RAG results (top 3 only, to stay within context).
    """
    rag = state.get("rag_context", [])
    if not rag:
        return "(Tidak ada RAG context tersedia.)"

    lines: list[str] = []
    for i, chunk in enumerate(rag[:3], start=1):  # cap at 3 to manage token budget
        title = chunk.get("title", "Unknown")
        text = chunk.get("text", "")[:400]  # trim long chunks
        score = chunk.get("score", 0)
        lines.append(f"[{i}] {title} (relevance: {score:.2f})\n{text}")
    return "\n\n".join(lines)


def _parse_analysis(raw: str) -> dict[str, str]:
    """Parse the JSON analysis from the LLM response.

    Args:
        raw: Raw string content from the LLM.

    Returns:
        A dict with the 5 analysis perspectives, or empty strings on parse failure.
    """
    import json

    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return {key: str(parsed.get(key, "")) for key in ANALYSIS_PERSPECTIVES}
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("[DeepDive] JSON parse failed: %s — raw: %s…", exc, text[:200])

    # Fallback: return empty placeholders
    return {key: "" for key in ANALYSIS_PERSPECTIVES}


# ─── Node function ─────────────────────────────────────────────────────────────

def deep_dive_node(state: ArcwrightState) -> dict[str, Any]:
    """LangGraph node: multi-perspective storytelling analysis.

    Reads ``story_fragments`` and ``rag_context`` from *state* and produces a
    structured analysis across five analytical lenses.

    Args:
        state: The shared ArcwrightState dict passed by LangGraph.

    Returns:
        A partial-state dict with keys:
        - ``deep_dive_analysis``: dict with keys surface, psychological,
          universal_theme, opposing_view, hidden_gold.
        - ``agent_notes``: list containing one AgentNote from this agent.
    """
    logger.info("[DeepDive] Node triggered.")

    fragments_text = _format_fragments(state)
    rag_text = _format_rag_context(state)

    empty_analysis = {key: "" for key in ANALYSIS_PERSPECTIVES}

    try:
        llm = _get_llm()

        user_prompt = (
            f"STORY FRAGMENTS:\n{fragments_text}\n\n"
            f"RAG CONTEXT (kutipan buku storytelling):\n{rag_text}\n\n"
            "Berikan analisis 5-perspektif dalam format JSON yang diminta."
        )

        response = llm.invoke(
            [
                SystemMessage(content=DEEP_DIVE_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
        )

        analysis = _parse_analysis(response.content)

        # ── Build summary note ────────────────────────────────────────────────
        hidden_gold_preview = (analysis.get("hidden_gold") or "")[:120]
        note_content = (
            f"Deep dive complete on {len(state.get('story_fragments', []))} fragment(s). "
            f"Hidden gold: '{hidden_gold_preview}…'"
        )

        logger.info("[DeepDive] Analysis complete.")

        return {
            "deep_dive_analysis": analysis,
            "agent_notes": [
                AgentNote(
                    agent="deep_dive",
                    note_type="insight",
                    content=note_content,
                )
            ],
        }

    except EnvironmentError as exc:
        logger.error("[DeepDive] Config error: %s", exc)
        return {
            "deep_dive_analysis": empty_analysis,
            "agent_notes": [
                AgentNote(
                    agent="deep_dive",
                    note_type="flag",
                    content=f"Config error: {exc}",
                )
            ],
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("[DeepDive] Unexpected error: %s", exc, exc_info=True)
        return {
            "deep_dive_analysis": empty_analysis,
            "agent_notes": [
                AgentNote(
                    agent="deep_dive",
                    note_type="flag",
                    content=f"Analysis failed: {type(exc).__name__}: {exc}",
                )
            ],
        }
