"""
Embedding & vector storage module.
Uses BAAI/bge-m3 (free, open-source, multilingual, 1024-dim).
Stores in ChromaDB (free, open-source, persistent).
"""
import json
import os
import time
import shutil
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

from . import config


def get_embedding_model(model_name: str = None) -> SentenceTransformer:
    """Load the sentence-transformers embedding model."""
    if model_name is None:
        model_name = config.EMBEDDING_MODEL
    print(f"  Loading embedding model: {model_name}...")
    return SentenceTransformer(model_name)


def get_chroma_client(chroma_dir: str = None) -> chromadb.PersistentClient:
    """Get or create a ChromaDB persistent client."""
    if chroma_dir is None:
        chroma_dir = str(config.CHROMA_DIR)
    return chromadb.PersistentClient(
        path=chroma_dir,
        settings=Settings(anonymized_telemetry=False)
    )


def embed_and_store(chunks: list, collection_name: str, 
                    embed_model: SentenceTransformer = None,
                    chroma_dir: str = None) -> dict:
    """
    Embed chunks and store in ChromaDB collection.
    
    Args:
        chunks: List of chunk dicts from chunk_markdown()
        collection_name: Name for the ChromaDB collection
        embed_model: Pre-loaded embedding model (or None to load)
        chroma_dir: ChromaDB storage directory
    
    Returns:
        Dict with collection info and stats
    """
    if embed_model is None:
        embed_model = get_embedding_model()
    
    client = get_chroma_client(chroma_dir)
    
    # Delete existing collection if it exists (fresh index)
    try:
        client.delete_collection(collection_name)
        print(f"  Removed existing collection: {collection_name}")
    except Exception:
        pass
    
    collection = client.create_collection(
        name=collection_name,
        metadata={"description": f"RAG collection — {len(chunks)} chunks"}
    )
    
    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [{
        "title": c["title"][:200],
        "section": c["section"][:200],
        "source": c["source"][:100],
        "char_count": str(c["char_count"]),
    } for c in chunks]
    
    # Batch embedding & storage
    batch_size = 32
    start = time.time()
    
    for i in range(0, len(chunks), batch_size):
        batch_end = min(i + batch_size, len(chunks))
        batch_texts = texts[i:batch_end]
        batch_ids = ids[i:batch_end]
        batch_metadatas = metadatas[i:batch_end]
        
        # Embed
        embeddings = embed_model.encode(batch_texts, show_progress_bar=False)
        
        # Store
        collection.add(
            ids=batch_ids,
            embeddings=embeddings.tolist(),
            documents=batch_texts,
            metadatas=batch_metadatas,
        )
    
    elapsed = time.time() - start
    stats = {
        "collection": collection_name,
        "chunk_count": len(chunks),
        "embed_time_s": round(elapsed, 1),
        "chroma_dir": str(chroma_dir or config.CHROMA_DIR),
    }
    
    print(f"  ✅ {len(chunks)} chunks embedded & stored in {elapsed:.1f}s")
    print(f"     Collection: {collection_name}")
    
    return stats


def list_collections(chroma_dir: str = None) -> list:
    """List all available ChromaDB collections."""
    client = get_chroma_client(chroma_dir)
    collections = client.list_collections()
    result = []
    for c in collections:
        result.append({
            "name": c.name,
            "count": c.count(),
            "metadata": c.metadata,
        })
    return result
