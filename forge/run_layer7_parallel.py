#!/usr/bin/env python3
"""
Layer 7: Embedding (BGE-M3) — Parallel processing (5 books)
Uses GPU (RTX 5060 Ti) with VRAM limit ~10GB.
NOTE: Prefer run_layer7_sequential.py to avoid OOM on 16GB VRAM.
      Use this only for targeted small batches.
"""
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add forge to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arcwright import config

# ─── Config ──────────────────────────────────────────────────
BOOKS = [
    "refined_the_anatomy_of_story_22_steps_to_becoming_a_master",
    "refined_how_to_tell_a_story",
    "refined_the_hero_with_a_thousand_faces_commemorative_editi",
    "refined_robert_mckee_story",
    "refined_storyworthy",
]
BATCH_SIZE  = 200
COLLECTION  = config.QDRANT_COLLECTION
QDRANT_URL  = config.QDRANT_URL
OUTPUT_DIR  = config.OUTPUT_DIR


def embed_book(book_dir_name: str) -> dict:
    """Embed a single book's enhanced chunks into Qdrant."""
    import torch
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    import uuid

    # Limit VRAM per process
    torch.cuda.set_per_process_memory_fraction(0.22)   # ~22% of 16GB = 3.5GB per process

    book_path     = OUTPUT_DIR / book_dir_name
    enhanced_file = book_path / "chunks_enhanced.json"

    if not enhanced_file.exists():
        return {"book": book_dir_name, "status": "error", "error": "No chunks_enhanced.json"}

    with open(enhanced_file) as f:
        chunks = json.load(f)

    print(f"[{book_dir_name}] Loading {len(chunks)} chunks...")

    # Load model on GPU
    model = SentenceTransformer("BAAI/bge-m3", device="cuda")

    # Qdrant client
    qdrant = QdrantClient(url=QDRANT_URL)

    # Ensure collection exists
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
        print(f"[{book_dir_name}] Created new collection: {COLLECTION}")
    else:
        count = qdrant.count(COLLECTION).count
        print(f"[{book_dir_name}] Collection exists: {count} vectors")

    # Embed in batches
    total_embedded = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch      = chunks[i:i + BATCH_SIZE]
        texts      = [c["text"] for c in batch]
        batch_ids  = [c["id"] for c in batch]
        metadatas  = [
            {
                "title":      c.get("title", "")[:200],
                "section":    c.get("section", "")[:200],
                "source":     c.get("source", "")[:100],
                "char_count": c.get("char_count", 0),
            }
            for c in batch
        ]

        embeddings = model.encode(texts, show_progress_bar=False, batch_size=32)

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, bid)),
                vector=emb.tolist(),
                payload={**meta, "text": text},
            )
            for bid, text, emb, meta in zip(batch_ids, texts, embeddings, metadatas)
        ]

        qdrant.upsert(collection_name=COLLECTION, points=points)

        total_embedded += len(batch)
        batch_num    = i // BATCH_SIZE + 1
        total_batches = (len(chunks) - 1) // BATCH_SIZE + 1
        print(f"[{book_dir_name}] Batch {batch_num}/{total_batches} done ({total_embedded}/{len(chunks)})")

    # Cleanup
    del model
    torch.cuda.empty_cache()

    return {"book": book_dir_name, "status": "success", "chunks": total_embedded}


def main():
    print(f"Layer 7 Parallel Embedding — {len(BOOKS)} books")
    print(f"   GPU: NVIDIA RTX 5060 Ti")
    print(f"   Collection: {COLLECTION}")
    print(f"   Qdrant: {QDRANT_URL}")
    print(f"   Batch size: {BATCH_SIZE}")
    print()

    # Process in parallel
    max_workers = 4   # 4 * ~3.5GB = ~14GB VRAM (tight but within 16GB)
    results     = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(embed_book, book): book for book in BOOKS}

        for future in as_completed(futures):
            book = futures[future]
            try:
                result = future.result()
                results.append(result)
                if result["status"] == "success":
                    print(f"OK  {book}: {result['chunks']} chunks embedded")
                else:
                    print(f"ERR {book}: {result['error']}")
            except Exception as e:
                print(f"ERR {book}: {e}")
                results.append({"book": book, "status": "error", "error": str(e)})

    # Summary
    print("\n" + "=" * 50)
    print("EMBEDDING SUMMARY")
    print("=" * 50)
    total = 0
    for r in results:
        mark   = "OK" if r["status"] == "success" else "ERR"
        chunks = r.get("chunks", 0)
        total += chunks
        print(f"  [{mark}] {r['book']}: {chunks} chunks")
    print(f"\nTotal: {total} chunks embedded into '{COLLECTION}' @ {QDRANT_URL}")


if __name__ == "__main__":
    main()
