"""
RAG Librarian Agent — connects to Arcwright Forge ChromaDB.
Read-only access to 9,270 chunks from 26 storytelling books.
Uses BGE-M3 embeddings (must match forge/arcwright/embed.py).
"""
import json
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools.retriever import create_retriever_tool
from langgraph.prebuilt import create_react_agent

from config import settings
from agents.state import ArcwrightState


_SYSTEM_PROMPT = """You are the RAG Librarian — keeper of storytelling wisdom.

Your ONLY job is to retrieve relevant storytelling knowledge from the library of 26 books.

When given a context or query:
1. Search the vector database for the most relevant techniques and frameworks
2. Return the framework/technique with source attribution: "[Book Title] — [Section/Chapter]"
3. Explain WHY it's relevant to the current story context
4. Prioritise actionable techniques over abstract theory
5. Do NOT suggest stories or converse with the user — only supply knowledge

Available knowledge includes: Hero's Journey, Save the Cat beat sheet, Story Spine,
Pixar storytelling rules, narrative psychology, audience resonance frameworks,
questioning techniques for story mining, emotional arc design, scene construction.

Always cite your source book and section."""


def _build_rag_tool():
    """Build the ChromaDB retriever tool. Lazy-loaded on first agent call."""
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vector_store = Chroma(
        client_settings=None,
        persist_directory=str(settings.CHROMA_DIR),
        embedding_function=embeddings,
        collection_name=settings.CHROMA_COLLECTION,
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
            "narrative frameworks (Hero's Journey, Save the Cat, Story Spine), "
            "audience psychology, emotional arc design, scene construction tips. "
            "Input should be a specific question or topic you want to learn about."
        ),
    )


# Module-level cache — loaded once per session
_rag_tool = None
_agent = None


def _get_agent(llm):
    global _rag_tool, _agent
    if _agent is None:
        _rag_tool = _build_rag_tool()
        _agent = create_react_agent(
            model=llm,
            tools=[_rag_tool],
            state_modifier=_SYSTEM_PROMPT,
        )
    return _agent


def rag_librarian_node(state: ArcwrightState, llm) -> dict:
    """
    RAG Librarian node — retrieves storytelling frameworks from ChromaDB.

    Reads:  story_fragments, current_phase
    Writes: rag_context (overwrite)
    """
    agent = _get_agent(llm)

    # Build query from current story fragments
    fragments_text = "\n".join(
        f"- {f['text']}" for f in state.get("story_fragments", [])
    )
    phase = state.get("current_phase", "mining")

    if phase == "mining":
        query = (
            "What are the best open-ended interviewing and story mining questions "
            "to help someone discover their personal story? "
            f"Context: {fragments_text or 'user has not shared anything yet'}"
        )
    else:
        query = (
            "What storytelling frameworks and narrative structures are most relevant "
            f"for a story with these themes: {fragments_text}"
        )

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    # Extract last AI message as RAG context
    rag_text = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.content:
            rag_text = msg.content
            break

    return {
        "rag_context": [{"query": query, "response": rag_text, "source": "chromadb"}]
    }
