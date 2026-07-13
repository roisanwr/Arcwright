"""Batch remaining books — only processes books NOT yet in ChromaDB."""
import os, sys, json, time, re
from pathlib import Path

# Add forge to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from arcwright import extract, chunk, config
from arcwright.embed import get_embedding_model, get_chroma_client

BOOKS_DIR = config.BOOKS_DIR
OUTPUT_DIR = config.OUTPUT_DIR
CHROMA_DIR = config.CHROMA_DIR
UNIFIED_COLLECTION = "storytelling_books"
INTERIM_FILE = OUTPUT_DIR / "batch_interim.json"

FORMAT_PREFERENCE = [".pdf", ".epub", ".mobi", ".azw3", ".docx", ".txt", ".html"]

def normalize_title(name):
    name = Path(name).stem
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'[:\\–—-].*$', '', name)
    name = re.sub(r'\b(the|a|an|of|and|by|for|in|to)\b', ' ', name, flags=re.I)
    name = re.sub(r'\s+', ' ', name).strip().lower()
    return name

def dedup_books(books):
    groups = {}
    for book_path in books:
        name = book_path.name
        ext = book_path.suffix.lower()
        if ext not in extract.SUPPORTED_FORMATS:
            continue
        norm = normalize_title(name)
        if norm not in groups:
            groups[norm] = []
        groups[norm].append((book_path, ext, book_path.stat().st_size))

    selected = []
    for norm, versions in groups.items():
        if len(versions) == 1:
            selected.append(versions[0][0])
        else:
            def pref(v):
                _, ext, _ = v
                try: return FORMAT_PREFERENCE.index(ext)
                except ValueError: return len(FORMAT_PREFERENCE)
            versions.sort(key=pref)
            selected.append(versions[0][0])
    return selected

def is_already_processed(book_path):
    """Check if book already has an output dir with chunks.json."""
    slug = re.sub(r'[^a-zA-Z0-9_]', '_', book_path.stem)[:50]
    book_output = OUTPUT_DIR / slug
    chunks_file = book_output / "chunks.json"
    if chunks_file.exists():
        with open(chunks_file) as f:
            chunks_list = json.load(f)
        if len(chunks_list) > 0:
            return True, len(chunks_list)
    return False, 0

def process_single_book(book_path, embed_model, chroma_client, unified_collection):
    """Process one book: extract → chunk → embed → ChromaDB."""
    result = {"file": str(book_path), "status": "error", "chunks": 0}

    try:
        file_name = book_path.stem
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', file_name)[:50]
        book_output = OUTPUT_DIR / slug
        book_output.mkdir(parents=True, exist_ok=True)

        # STEP 1: Extract
        print(f"  📄 Extracting...", flush=True)
        markdown = extract.extract_file(str(book_path), force_ocr=True)
        md_path = book_output / "extracted.md"
        md_path.write_text(markdown, encoding="utf-8")
        print(f"     Saved: {md_path.name} ({len(markdown):,} chars)", flush=True)

        # STEP 2: Chunk
        print(f"  ✂️  Chunking...", flush=True)
        chunks_list = chunk.chunk_markdown(markdown, source_name=file_name)
        chunks_path = book_output / "chunks.json"
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(chunks_list, f, indent=2, ensure_ascii=False)

        print(f"     {len(chunks_list)} chunks generated", flush=True)

        if not chunks_list:
            result["error"] = "No chunks generated"
            return result

        # STEP 3: Embed + ChromaDB
        print(f"  🧠 Embedding & adding to ChromaDB...", flush=True)
        ids = [c["id"] for c in chunks_list]
        texts = [c["text"] for c in chunks_list]
        metadatas = [{
            "title": c["title"][:200],
            "section": c["section"][:200],
            "source": c["source"][:100],
            "book_slug": slug,
            "char_count": str(c["char_count"]),
        } for c in chunks_list]

        batch_size = 32
        for i in range(0, len(chunks_list), batch_size):
            batch_end = min(i + batch_size, len(chunks_list))
            batch_texts = texts[i:batch_end]
            batch_ids = ids[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            embeddings = embed_model.encode(batch_texts, show_progress_bar=False)
            unified_collection.add(
                ids=batch_ids, embeddings=embeddings.tolist(),
                documents=batch_texts, metadatas=batch_metadatas,
            )

        result["status"] = "completed"
        result["chunks"] = len(chunks_list)

    except Exception as e:
        result["error"] = str(e)
        import traceback
        traceback.print_exc()

    return result

def save_interim(processed, failed, current, total):
    """Save interim progress so cron can read it."""
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "processed": processed,
        "failed": failed,
        "current_book": current,
        "total_books": total,
        "status": "running",
    }
    with open(INTERIM_FILE, "w") as f:
        json.dump(data, f, indent=2)

def main():
    print("=" * 60)
    print("  📚 ARCRIGHT BATCH — REMAINING BOOKS ONLY")
    print("=" * 60)

    # Find all books
    all_books = sorted(BOOKS_DIR.glob("*"))
    supported = [b for b in all_books if b.suffix.lower() in extract.SUPPORTED_FORMATS]
    print(f"  Total files: {len(supported)}")

    # Dedup
    unique_books = dedup_books(supported)
    print(f"  Unique books (after dedup): {len(unique_books)}")

    # Filter out already processed
    to_process = []
    already_done = 0
    for book in unique_books:
        done, chunk_count = is_already_processed(book)
        if done:
            already_done += 1
            print(f"  ⏩ Already processed: {book.name} ({chunk_count} chunks)")
        else:
            to_process.append(book)

    print(f"\n  ✅ Already processed: {already_done}")
    print(f"  📄 Remaining to process: {len(to_process)}")

    if not to_process:
        print("\n  🎉 ALL BOOKS ALREADY PROCESSED!")
        # Write final interim
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "processed": 0,
            "failed": 0,
            "current_book": "ALL DONE",
            "total_books": 0,
            "status": "completed",
            "note": "All books already processed in previous batch"
        }
        with open(INTERIM_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return

    # Load embedding model
    print(f"\n  🧠 Loading embedding model ({config.EMBEDDING_MODEL})...", flush=True)
    embed_model = get_embedding_model()
    print(f"     ✅ Model loaded", flush=True)

    # ChromaDB client
    chroma_client = get_chroma_client()
    try:
        unified = chroma_client.get_collection(UNIFIED_COLLECTION)
        existing = unified.count()
        print(f"  📂 Unified collection: {UNIFIED_COLLECTION} ({existing:,} chunks)", flush=True)
    except Exception:
        unified = chroma_client.create_collection(
            name=UNIFIED_COLLECTION,
            metadata={"description": "Arcwright Storytelling Books RAG"}
        )
        print(f"  📂 Created new collection: {UNIFIED_COLLECTION}", flush=True)

    # Process each remaining book
    completed_list = []
    failed_list = []
    total_start = time.time()

    for i, book_path in enumerate(to_process, 1):
        print(f"\n{'='*50}", flush=True)
        print(f"  [{i}/{len(to_process)}] {book_path.name}", flush=True)
        print(f"{'='*50}", flush=True)

        book_start = time.time()
        result = process_single_book(book_path, embed_model, chroma_client, unified)
        elapsed = time.time() - book_start

        if result["status"] == "completed":
            print(f"  ✅ Done in {elapsed:.1f}s — {result['chunks']} chunks", flush=True)
            completed_list.append(result)
        else:
            print(f"  ❌ FAILED: {result.get('error', 'Unknown')}", flush=True)
            failed_list.append(result)

        # Save interim
        save_interim(
            processed=len(completed_list),
            failed=len(failed_list),
            current=book_path.name,
            total=len(to_process),
        )

    # Final summary
    total_time = time.time() - total_start
    final_count = unified.count()

    print(f"\n{'='*60}", flush=True)
    print(f"  📊 BATCH COMPLETE!", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"  ✅ {len(completed_list)}/{len(to_process)} books processed", flush=True)
    print(f"  ❌ {len(failed_list)} failed", flush=True)
    print(f"  📚 Total chunks in ChromaDB: {final_count:,}", flush=True)
    print(f"  ⏱️  Total time: {total_time:.1f}s ({total_time/60:.1f} min)", flush=True)

    if failed_list:
        print(f"\n  Failed books:")
        for f in failed_list:
            print(f"    ❌ {Path(f['file']).name}: {f.get('error', 'Unknown')}")

    # Save final interim
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "processed": len(completed_list),
        "failed": len(failed_list),
        "current_book": "COMPLETE",
        "total_books": len(to_process),
        "status": "completed",
        "total_chunks": final_count,
        "total_time_s": round(total_time, 1),
        "completed_books": [Path(b["file"]).name for b in completed_list],
        "failed_books": [{"file": Path(b["file"]).name, "error": b.get("error")} for b in failed_list],
    }
    with open(INTERIM_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n  📄 Interim report: {INTERIM_FILE}", flush=True)
    print(f"{'='*60}", flush=True)

if __name__ == "__main__":
    main()
