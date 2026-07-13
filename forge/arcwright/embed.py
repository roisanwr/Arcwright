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
                    chroma_dir: str = None,
                    replace: bool = False) -> dict:
    """
    Embed chunks and store in ChromaDB collection.
    
    Args:
        chunks: List of chunk dicts from chunk_markdown()
        collection_name: Name for the ChromaDB collection
        embed_model: Pre-loaded embedding model (or None to load)
        chroma_dir: ChromaDB storage directory
        replace: If True, delete and recreate the collection (default: False — append)
    
    Returns:
        Dict with collection info and stats
    """
    if embed_model is None:
        embed_model = get_embedding_model()
    
    client = get_chroma_client(chroma_dir)
    
    if replace:
        # Delete existing collection if it exists (fresh index)
        try:
            client.delete_collection(collection_name)
            print(f"  Removed existing collection: {collection_name}")
        except Exception:
            pass
    
    # Get or create collection (append mode by default)
    try:
        collection = client.get_collection(collection_name)
        existing_count = collection.count()
        print(f"  Using existing collection: {collection_name} ({existing_count} existing chunks)")
    except Exception:
        collection = client.create_collection(
            name=collection_name,
            metadata={"description": f"RAG collection — Arcwright pipeline"}
        )
        existing_count = 0
        print(f"  Created new collection: {collection_name}")
    
    # Filter out IDs already in collection
    existing_ids = set(collection.get()["ids"]) if existing_count > 0 else set()
    new_chunks = [c for c in chunks if c["id"] not in existing_ids]
    
    if not new_chunks:
        print(f"  ⏩ All {len(chunks)} chunks already exist in collection — skipping")
        return {
            "collection": collection_name,
            "chunk_count": 0,
            "embed_time_s": 0,
            "chroma_dir": str(chroma_dir or config.CHROMA_DIR),
            "existing_count": existing_count,
            "new_count": 0,
        }
    
    ids = [c["id"] for c in new_chunks]
    texts = [c["text"] for c in new_chunks]
    metadatas = [{
        "title": c["title"][:200],
        "section": c["section"][:200],
        "source": c["source"][:100],
        "char_count": str(c["char_count"]),
    } for c in new_chunks]
    
    # Batch embedding & storage
    batch_size = 32
    start = time.time()
    
    for i in range(0, len(new_chunks), batch_size):
        batch_end = min(i + batch_size, len(new_chunks))
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
    total_count = existing_count + len(new_chunks)
    stats = {
        "collection": collection_name,
        "chunk_count": total_count,
        "existing_count": existing_count,
        "new_count": len(new_chunks),
        "embed_time_s": round(elapsed, 1),
        "chroma_dir": str(chroma_dir or config.CHROMA_DIR),
    }
    
    print(f"  ✅ {len(new_chunks)} new chunks embedded & stored in {elapsed:.1f}s")
    print(f"     Collection: {collection_name} ({total_count} total)")
    
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
