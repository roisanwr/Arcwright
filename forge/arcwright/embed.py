"""
Embedding & vector storage module.
Uses BAAI/bge-m3 (free, open-source, multilingual, 1024-dim).
Stores in Qdrant (Docker, OS-agnostic, production-grade).
"""
import uuid
import time
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, PayloadSchemaType
)

from . import config


def get_embedding_model(model_name: str = None) -> SentenceTransformer:
    """Load the sentence-transformers embedding model."""
    if model_name is None:
        model_name = config.EMBEDDING_MODEL
    print(f"  Loading embedding model: {model_name}...")
    return SentenceTransformer(model_name)


def get_qdrant_client(url: str = None) -> QdrantClient:
    """Connect ke Qdrant server (Docker)."""
    if url is None:
        url = config.QDRANT_URL
    return QdrantClient(url=url)


def ensure_collection(client: QdrantClient, collection_name: str, replace: bool = False):
    """Buat collection jika belum ada, atau hapus dan buat ulang jika replace=True."""
    existing = [c.name for c in client.get_collections().collections]

    if replace and collection_name in existing:
        client.delete_collection(collection_name)
        print(f"  Removed existing collection: {collection_name}")
        existing = []

    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
        # Payload index untuk filter cepat berdasarkan metadata
        client.create_payload_index(collection_name, "source", PayloadSchemaType.KEYWORD)
        client.create_payload_index(collection_name, "title",  PayloadSchemaType.KEYWORD)
        print(f"  Created new collection: {collection_name}")


def embed_and_store(chunks: list, collection_name: str,
                    embed_model: SentenceTransformer = None,
                    qdrant_url: str = None,
                    replace: bool = False) -> dict:
    """
    Embed chunks dan simpan ke Qdrant collection.

    Args:
        chunks:          List of chunk dicts dari chunk_markdown()
        collection_name: Nama collection Qdrant
        embed_model:     Pre-loaded embedding model (atau None untuk load otomatis)
        qdrant_url:      URL Qdrant server (default: dari config)
        replace:         Jika True, hapus dan buat ulang collection

    Returns:
        Dict dengan statistik hasil embedding
    """
    if embed_model is None:
        embed_model = get_embedding_model()

    client = get_qdrant_client(qdrant_url)
    ensure_collection(client, collection_name, replace=replace)

    existing_count = client.count(collection_name).count

    # Build points
    texts     = [c["text"] for c in chunks]
    ids       = [c["id"] for c in chunks]
    metadatas = [
        {
            "title":      c["title"][:200],
            "section":    c["section"][:200],
            "source":     c["source"][:100],
            "char_count": c["char_count"],
        }
        for c in chunks
    ]

    # Embed dalam batch
    batch_size = 32
    start      = time.time()
    all_points: list[PointStruct] = []

    for i in range(0, len(chunks), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_ids   = ids[i:i + batch_size]
        batch_meta  = metadatas[i:i + batch_size]

        embeddings = embed_model.encode(batch_texts, show_progress_bar=False)

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, bid)),   # string ID → deterministic UUID
                vector=emb.tolist(),
                payload={**meta, "text": text},
            )
            for bid, text, emb, meta in zip(batch_ids, batch_texts, embeddings, batch_meta)
        ]
        all_points.extend(points)

    # Upload ke Qdrant dalam batch besar
    UPLOAD_BATCH = 200
    for i in range(0, len(all_points), UPLOAD_BATCH):
        client.upsert(
            collection_name=collection_name,
            points=all_points[i:i + UPLOAD_BATCH],
        )

    elapsed   = time.time() - start
    new_count = client.count(collection_name).count

    print(f"  {len(chunks)} chunks embedded & stored in {elapsed:.1f}s")
    print(f"     Collection: {collection_name} ({new_count} total)")

    return {
        "collection":    collection_name,
        "chunk_count":   new_count,
        "existing_count": existing_count,
        "new_count":     len(chunks),
        "embed_time_s":  round(elapsed, 1),
        "qdrant_url":    qdrant_url or config.QDRANT_URL,
    }


def list_collections(qdrant_url: str = None) -> list:
    """List semua Qdrant collections yang tersedia."""
    client      = get_qdrant_client(qdrant_url)
    collections = client.get_collections().collections
    return [
        {
            "name":  c.name,
            "count": client.count(c.name).count,
        }
        for c in collections
    ]
