"""
rag_librarian.py — RAG Librarian Agent for Arcwright Storytelling AI.

Connects to the existing ChromaDB vector store and retrieves semantically
relevant storytelling knowledge chunks based on the user's story fragments.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from agents.state import AgentNote, ArcwrightState

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

CHROMA_DB_PATH = "/home/rois/Arcwright/forge/output/chroma_db"
COLLECTION_NAME = "storytelling_books"
EMBEDDING_MODEL = "BAAI/bge-m3"
TOP_K = 5


# ─── Singleton embedding loader ───────────────────────────────────────────────

_embeddings: HuggingFaceEmbeddings | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Return a cached HuggingFaceEmbeddings instance (loaded once per process)."""
    global _embeddings
    if _embeddings is None:
        logger.info("Loading embedding model '%s' …", EMBEDDING_MODEL)
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


# ─── Helper: build semantic query ─────────────────────────────────────────────

def _build_query(state: ArcwrightState) -> str:
    """Combine story fragments into a single semantic search query.

    Args:
        state: The current ArcwrightState holding story_fragments.

    Returns:
        A plain-text query string derived from all fragment text/themes.
    """
    fragments = state.get("story_fragments", [])
    if not fragments:
        return "storytelling techniques emotional narrative"

    parts: list[str] = []
    for frag in fragments:
        if frag.get("text"):
            parts.append(frag["text"])
        if frag.get("theme"):
            parts.append(frag["theme"])
        if frag.get("emotion"):
            parts.append(frag["emotion"])

    query = " ".join(parts)
    # Trim to a reasonable length so embeddings stay focused
    return query[:1000] if len(query) > 1000 else query


# ─── Node function ─────────────────────────────────────────────────────────────

def rag_librarian_node(state: ArcwrightState) -> dict[str, Any]:
    """LangGraph node: retrieve storytelling knowledge relevant to user fragments.

    Reads ``story_fragments`` from *state*, constructs a semantic query, and
    performs a similarity search against the Arcwright ChromaDB collection.

    Args:
        state: The shared ArcwrightState dict passed by LangGraph.

    Returns:
        A partial-state dict with keys:
        - ``rag_context``: list of dicts with keys text, title, source, score.
        - ``agent_notes``: list containing one AgentNote from this agent.
    """
    logger.info("[RAGLibrarian] Node triggered.")

    # ── Validate ChromaDB path ────────────────────────────────────────────────
    db_path = Path(CHROMA_DB_PATH)
    if not db_path.exists():
        logger.warning("[RAGLibrarian] ChromaDB path not found: %s", db_path)
        return {
            "rag_context": [],
            "agent_notes": [
                AgentNote(
                    agent="rag_librarian",
                    note_type="flag",
                    content=f"ChromaDB path not found: {CHROMA_DB_PATH}",
                )
            ],
        }

    try:
        # ── Load embeddings + vector store ───────────────────────────────────
        embeddings = _get_embeddings()
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH,
        )

        # ── Build query and search ────────────────────────────────────────────
        query = _build_query(state)
        logger.info("[RAGLibrarian] Query: %s …", query[:120])

        results = vectorstore.similarity_search_with_relevance_scores(
            query=query,
            k=TOP_K,
        )

        # ── Format results ────────────────────────────────────────────────────
        rag_context: list[dict[str, Any]] = []
        for doc, score in results:
            rag_context.append(
                {
                    "text": doc.page_content,
                    "title": doc.metadata.get("title", "Unknown"),
                    "source": doc.metadata.get("source", doc.metadata.get("file", "Unknown")),
                    "score": round(float(score), 4),
                }
            )

        note_content = (
            f"Retrieved {len(rag_context)} chunks from '{COLLECTION_NAME}'. "
            f"Top score: {rag_context[0]['score'] if rag_context else 'N/A'}. "
            f"Query preview: '{query[:80]}…'"
        )
        logger.info("[RAGLibrarian] Retrieved %d results.", len(rag_context))

        return {
            "rag_context": rag_context,
            "agent_notes": [
                AgentNote(
                    agent="rag_librarian",
                    note_type="insight",
                    content=note_content,
                )
            ],
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("[RAGLibrarian] Error during retrieval: %s", exc, exc_info=True)
        return {
            "rag_context": [],
            "agent_notes": [
                AgentNote(
                    agent="rag_librarian",
                    note_type="flag",
                    content=f"RAG retrieval failed: {type(exc).__name__}: {exc}",
                )
            ],
        }
