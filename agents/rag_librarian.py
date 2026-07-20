"""
RAG Librarian Agent — connects to Arcwright Forge Qdrant vector store.
Read-only access to 9,270 chunks from 26 storytelling books.
Uses BGE-M3 embeddings (must match forge/arcwright/embed.py).

Dipanggil dalam 4 konteks berbeda (query_purpose):
  1. "mining_bootstrap"  — sebelum interview pertama, ambil teknik bertanya terbaik
  2. "mining_probe"      — tiap ada fragment baru, ambil teknik menggali lebih dalam
  3. "enriching"         — saat enriching phase, cari framework naratif yang cocok
  4. "outlining"         — saat outlining, cari struktur terbaik untuk tema ini
  5. "scripting"         — saat script writing, cari teknik penulisan platform-specific
"""
import json
from datetime import datetime
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_core.tools.retriever import create_retriever_tool
from langgraph.prebuilt import create_react_agent

from config import settings
from agents.state import ArcwrightState, RAGResult, RAGChunk, ThoughtProcess


_SYSTEM_PROMPT = """You are the RAG Librarian — keeper of storytelling wisdom from 26 master books.

Your ONLY job is to retrieve and synthesize relevant storytelling knowledge.

When given a context or query:
1. Use the search_storytelling_knowledge tool to find the MOST relevant techniques
2. Make 1-3 targeted searches with specific queries (not one generic query)
3. Synthesize the retrieved chunks into actionable guidance
4. ALWAYS cite your source: "[Book Title] — [Section/Chapter]"
5. Be SPECIFIC and ACTIONABLE — not abstract theory

Output format (ALWAYS end with this JSON block):
[RAG_SYNTHESIS]:
{
  "synthesis": "<actionable guidance synthesized from the retrieved chunks>",
  "source_books": ["<Book Title 1>", "<Book Title 2>"],
  "key_technique": "<the single most applicable technique name>",
  "application": "<exactly how to apply this to the current situation>"
}

DO NOT output general advice. Be specific to the story context provided."""


# ── Module-level cache ────────────────────────────────────────────────────────
_rag_tool = None
_agent_cache: dict = {}    # keyed by llm identity


def _build_rag_tool():
    """Build the Qdrant retriever tool. Lazy-loaded on first call."""
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )
    qdrant_client = QdrantClient(url=settings.QDRANT_URL)
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=settings.QDRANT_COLLECTION,
        embedding=embeddings,
    )
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": settings.RAG_K, "fetch_k": settings.RAG_FETCH_K},
    )
    return create_retriever_tool(
        retriever,
        name="search_storytelling_knowledge",
        description=(
            "Search the storytelling knowledge base (26 books, 9270 chunks). "
            "Use this to find: questioning techniques for story mining, "
            "narrative frameworks (Hero's Journey, Save the Cat, Story Spine, Pixar rules), "
            "audience psychology, emotional arc design, scene construction, "
            "platform-specific writing techniques. "
            "Input should be a SPECIFIC question or topic. "
            "Call this tool MULTIPLE TIMES with different queries for best results."
        ),
    )


def _get_agent(llm):
    global _rag_tool, _agent_cache
    llm_id = id(llm)
    if llm_id not in _agent_cache:
        if _rag_tool is None:
            _rag_tool = _build_rag_tool()
        _agent_cache[llm_id] = create_react_agent(
            model=llm,
            tools=[_rag_tool],
            prompt=_SYSTEM_PROMPT,
        )
    return _agent_cache[llm_id]


def _build_query(state: ArcwrightState, purpose: str) -> str:
    """Build a targeted query based on the purpose and current state context."""
    fragments = state.get("story_fragments", [])
    platform = state.get("user_profile", {}).get("platform_target", "general")

    if purpose == "mining_bootstrap":
        return (
            "What are the BEST opening interview questions to help someone discover "
            "a compelling personal story they haven't realized is worth telling? "
            "Include: contrast questions, sensory questions, and the Storyworthy "
            "'5-second moment' technique. How do I make someone feel safe sharing?"
        )

    if purpose == "mining_probe" and fragments:
        latest = fragments[-1]
        emotion = latest.get("emotion", "unknown")
        text = latest.get("text", "")
        # Analisis apakah ada karakter, konflik, sensory detail yang masih kurang
        missing = _identify_missing_elements(fragments)
        return (
            f"The user shared: \"{text[:300]}\" (emotion: {emotion}).\n\n"
            f"Missing story elements that need to be extracted: {missing}\n\n"
            f"What specific follow-up questions from storytelling masters (Storyworthy, "
            f"Bird by Bird, Story) would help extract: {missing}? "
            f"Give me concrete question examples."
        )

    if purpose == "enriching" and fragments:
        themes = " | ".join(f.get("text", "")[:80] for f in fragments[:3])
        emotions = list({f.get("emotion", "") for f in fragments if f.get("emotion")})
        return (
            f"Story themes: {themes}\n"
            f"Core emotions: {', '.join(emotions)}\n\n"
            f"What narrative FRAMEWORK (Hero's Journey, Save the Cat, Story Spine, etc.) "
            f"best fits a story with these themes and emotional arc? "
            f"And what storytelling techniques would make this most resonant on {platform}?"
        )

    if purpose == "outlining" and fragments:
        themes = " | ".join(f.get("text", "")[:80] for f in fragments[:3])
        return (
            f"I'm creating a story outline for {platform} about: {themes}\n\n"
            f"What SPECIFIC structural techniques should I use for: "
            f"1) The opening hook, 2) The turning point reveal, 3) The emotional punchline? "
            f"Reference specific books and sections."
        )

    if purpose == "scripting":
        outline = state.get("story_outline", {})
        return (
            f"Platform: {platform}\n"
            f"Story title: {outline.get('title', '')}\n"
            f"Tone of story: {outline.get('hook', '')[:100]}\n\n"
            f"What are the BEST writing techniques for {platform} storytelling? "
            f"How should I structure sentences for maximum impact? "
            f"What does [Bird by Bird / On Writing / Storyworthy] say about "
            f"writing this type of emotional story?"
        )

    # Generic fallback
    return "What are the most powerful storytelling frameworks for personal narratives?"


def _identify_missing_elements(fragments: list) -> str:
    """Identify what story elements are still missing from the fragments."""
    all_text = " ".join(f.get("text", "") for f in fragments).lower()

    missing = []
    # Check for sensory details
    sensory_words = ["saw", "heard", "felt", "smelled", "tasted", "lihat", "dengar", "rasa"]
    if not any(w in all_text for w in sensory_words):
        missing.append("sensory details (what did they see/hear/feel?)")

    # Check for specific characters
    if len(fragments) > 0 and not any(
        keyword in all_text for keyword in ["dia", "mereka", "teman", "keluarga", "he ", "she ", "they ", "friend", "family", "boss"]
    ):
        missing.append("specific characters (who else was there?)")

    # Check for conflict/tension
    if not any(w in all_text for w in ["tapi", "tapi", "but", "however", "though", "konflik", "masalah", "problem", "struggle"]):
        missing.append("tension or conflict (what was the obstacle?)")

    # Check for a clear moment (turning point)
    if len(fragments) < 2:
        missing.append("specific moment (the exact instant things changed)")

    return ", ".join(missing) if missing else "deeper emotional specificity"


def _extract_rag_chunks_from_result(result: dict) -> tuple[list[RAGChunk], str]:
    """Extract individual chunks and synthesis from agent result messages."""
    chunks = []
    synthesis = ""
    source_books = []

    messages = result.get("messages", [])

    # Extract tool call results (these are the raw Qdrant chunks)
    for msg in messages:
        if hasattr(msg, "type") and msg.type == "tool":
            # Tool messages contain the raw retrieved documents
            content = getattr(msg, "content", "")
            if content:
                # Each retrieved doc is separated
                docs = content.split("\n\n") if isinstance(content, str) else [str(content)]
                for doc in docs:
                    if doc.strip():
                        chunks.append(RAGChunk(
                            text=doc.strip(),
                            source="Storytelling Knowledge Base",
                            relevance_score=0.0,
                        ))

    # Extract synthesis from last AI message
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            import re, json as _json
            pattern = r"\[RAG_SYNTHESIS\]:\s*(\{[\s\S]+?\})\s*$"
            match = re.search(pattern, msg.content)
            if match:
                try:
                    data = _json.loads(match.group(1))
                    synthesis = data.get("synthesis", "")
                    source_books = data.get("source_books", [])
                except Exception:
                    synthesis = msg.content
            else:
                synthesis = msg.content
            break

    return chunks, synthesis, source_books


def rag_librarian_node(state: ArcwrightState, llm) -> dict:
    """
    RAG Librarian node — retrieves storytelling frameworks from Qdrant.
    
    Dipanggil dengan purpose berbeda:
      - mining_bootstrap : sebelum interview pertama
      - mining_probe     : tiap ada fragment baru
      - enriching        : saat enriching phase
      - outlining        : saat outlining
      - scripting        : saat script writing

    Reads:  story_fragments, current_phase, rag_bootstrapped
    Writes: rag_results (append), rag_context (legacy compat), rag_fragment_count, rag_bootstrapped
    """
    agent = _get_agent(llm)

    fragments = state.get("story_fragments", [])
    phase = state.get("current_phase", "mining")
    bootstrapped = state.get("rag_bootstrapped", False)

    # Determine purpose from context
    if not bootstrapped:
        purpose = "mining_bootstrap"
    elif phase == "mining":
        purpose = "mining_probe"
    elif phase == "enriching":
        purpose = "enriching"
    elif phase == "outlining":
        purpose = "outlining"
    elif phase == "scripting":
        purpose = "scripting"
    else:
        purpose = "mining_probe"

    thought = ThoughtProcess(
        agent="rag_librarian",
        timestamp=datetime.now().isoformat(),
        thought=f"Querying Qdrant for purpose='{purpose}' with {len(fragments)} fragments.",
        data={"purpose": purpose, "fragment_count": len(fragments)}
    )

    query = _build_query(state, purpose)
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    chunks, synthesis, source_books = _extract_rag_chunks_from_result(result)

    # Build structured RAGResult
    rag_result = RAGResult(
        query=query,
        chunks=chunks,
        synthesis=synthesis,
        source_books=source_books,
        query_purpose=purpose,
    )

    # Legacy compat: keep rag_context as before (untuk agent yang masih pakai format lama)
    legacy_rag_context = [{
        "query": query,
        "response": synthesis,  # Full synthesis, tidak di-truncate
        "source": "qdrant",
        "fragments_processed": len(fragments),
        "source_books": source_books,
        "chunks": chunks,       # Full chunks tersedia
    }]

    updates = {
        "rag_results": [rag_result],
        "rag_context": legacy_rag_context,
        "rag_fragment_count": len(fragments),
        "thought_process": [thought],
    }

    if not bootstrapped:
        updates["rag_bootstrapped"] = True

    return updates
