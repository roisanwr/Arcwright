#!/usr/bin/env python3
"""
Layer 7: Embedding (BGE-M3) — Parallel processing for 5 books
Uses GPU (RTX 5060 Ti) with VRAM limit ~10GB
"""
import sys
import json
import time
import os
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add forge to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arcwright import config

# ─── Config ──────────────────────────────────────────────
BOOKS = [
    "refined_the_anatomy_of_story_22_steps_to_becoming_a_master",
    "refined_how_to_tell_a_story",
    "refined_the_hero_with_a_thousand_faces_commemorative_editi",
    "refined_robert_mckee_story",
    "refined_storyworthy",
]
BATCH_SIZE = 200
COLLECTION = "storytelling_books"
CHROMA_DIR = config.CHROMA_DIR
OUTPUT_DIR = config.OUTPUT_DIR

def embed_book(book_dir_name: str) -> dict:
    """Embed a single book's enhanced chunks into ChromaDB."""
    import torch
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings

    # Limit VRAM per process
    torch.cuda.set_per_process_memory_fraction(0.22)  # ~20% of 16GB = 3.2GB per process

    book_path = OUTPUT_DIR / book_dir_name
    enhanced_file = book_path / "chunks_enhanced.json"
    
    if not enhanced_file.exists():
        return {"book": book_dir_name, "status": "error", "error": "No chunks_enhanced.json"}

    with open(enhanced_file) as f:
        chunks = json.load(f)

    print(f"[{book_dir_name}] Loading {len(chunks)} chunks...")

    # Load model on GPU
    model = SentenceTransformer("BAAI/bge-m3", device="cuda")
    
    # ChromaDB client
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Get or create collection
    try:
        collection = client.get_collection(COLLECTION)
        print(f"[{book_dir_name}] Collection exists: {collection.count()} docs")
    except:
        collection = client.create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"[{book_dir_name}] Created new collection")

    # Embed in batches
    total_embedded = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = []
        for c in batch:
            meta = {k: v for k, v in c.items() if k not in ("text", "id")}
            # ChromaDB doesn't support nested objects
            meta = {k: str(v) if isinstance(v, (dict, list)) else v for k, v in meta.items()}
            metadatas.append(meta)

        # Embed
        embeddings = model.encode(texts, show_progress_bar=False, batch_size=32)
        
        # Upsert to ChromaDB
        collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas
        )
        
        total_embedded += len(batch)
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(chunks) - 1) // BATCH_SIZE + 1
        print(f"[{book_dir_name}] Batch {batch_num}/{total_batches} done ({total_embedded}/{len(chunks)})")

    # Cleanup
    del model
    torch.cuda.empty_cache()

    return {"book": book_dir_name, "status": "success", "chunks": total_embedded}


def main():
    print(f"🚀 Layer 7 Parallel Embedding — {len(BOOKS)} books")
    print(f"   GPU: NVIDIA RTX 5060 Ti")
    print(f"   Collection: {COLLECTION}")
    print(f"   ChromaDB: {CHROMA_DIR}")
    print(f"   Batch size: {BATCH_SIZE}")
    print()

    # Process in parallel
    max_workers = 4  # 4 * ~2.5GB = ~10GB VRAM
    results = []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(embed_book, book): book for book in BOOKS}
        
        for future in as_completed(futures):
            book = futures[future]
            try:
                result = future.result()
                results.append(result)
                if result["status"] == "success":
                    print(f"✅ {book}: {result['chunks']} chunks embedded")
                else:
                    print(f"❌ {book}: {result['error']}")
            except Exception as e:
                print(f"❌ {book}: {e}")
                results.append({"book": book, "status": "error", "error": str(e)})

    # Summary
    print("\n" + "="*50)
    print("📊 EMBEDDING SUMMARY")
    print("="*50)
    total = 0
    for r in results:
        status = "✅" if r["status"] == "success" else "❌"
        chunks = r.get("chunks", 0)
        total += chunks
        print(f"  {status} {r['book']}: {chunks} chunks")
    print(f"\nTotal: {total} chunks embedded into '{COLLECTION}'")

if __name__ == "__main__":
    main()