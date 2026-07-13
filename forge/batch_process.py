"""
Batch processing script for Arcwright storytelling books.
Processes all books in forge/data/books/ through the RAG pipeline.

Features:
- Deduplicates books (same title, different format — picks best)
- Per-book output: extracted.md + chunks.json
- Unified ChromaDB collection: "storytelling_books"
- Progress tracking and error recovery
"""

import os
import sys
import json
import time
import re
from pathlib import Path

# Add forge to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arcwright import extract, chunk, config
from arcwright.embed import get_embedding_model, get_chroma_client

# ─── Config ──────────────────────────────────────────────────────

BOOKS_DIR = config.BOOKS_DIR
OUTPUT_DIR = config.OUTPUT_DIR
CHROMA_DIR = config.CHROMA_DIR
UNIFIED_COLLECTION = "storytelling_books"

# Format preference: prefer formats with better extraction quality
FORMAT_PREFERENCE = [".pdf", ".epub", ".mobi", ".azw3", ".docx", ".txt", ".html"]


# ─── Dedup Logic ─────────────────────────────────────────────────

def normalize_title(name: str) -> str:
    """Normalize book title for dedup comparison."""
    # Remove extension
    name = Path(name).stem
    # Remove author parentheticals
    name = re.sub(r'\([^)]*\)', '', name)
    # Remove subtitle after common delimiters
    name = re.sub(r'[:\\–—-].*$', '', name)
    # Remove common suffixes
    name = re.sub(r'\b(the|a|an|of|and|by|for|in|to)\b', ' ', name, flags=re.I)
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip().lower()
    return name


def dedup_books(books: list) -> list:
    """
    Group books by normalized title, pick best format per group.
    Returns list of selected file paths.
    """
    groups = {}  # normalized_title → [(path, ext, size)]
    
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
    skipped = []
    
    for norm, versions in groups.items():
        if len(versions) == 1:
            selected.append(versions[0][0])
        else:
            # Sort by format preference
            def pref(v):
                _, ext, _ = v
                try:
                    return FORMAT_PREFERENCE.index(ext)
                except ValueError:
                    return len(FORMAT_PREFERENCE)
            
            versions.sort(key=pref)
            best = versions[0]
            selected.append(best[0])
            
            # Log what was skipped
            for v in versions[1:]:
                skipped.append((v[0], best[0]))
    
    # Report
    if skipped:
        print(f"\n📊 Dedup Summary:")
        for dup, kept in skipped:
            print(f"  ⏩ {dup.name}")
            print(f"     → Kept: {kept.name}")
    
    return selected


# ─── Batch Processing ────────────────────────────────────────────

def process_all_books():
    """Process all books and create unified ChromaDB collection."""
    
    print(f"{'='*60}")
    print(f"  📚 ARCRIGHT BATCH RAG PIPELINE")
    print(f"{'='*60}")
    print(f"  Books dir: {BOOKS_DIR}")
    print(f"  Output dir: {OUTPUT_DIR}")
    print(f"  ChromaDB: {CHROMA_DIR}")
    print(f"  Unified collection: {UNIFIED_COLLECTION}")
    print(f"{'='*60}\n")
    
    # Find all books
    all_books = sorted(BOOKS_DIR.glob("*"))
    supported = [b for b in all_books if b.suffix.lower() in extract.SUPPORTED_FORMATS]
    unsupported = [b for b in all_books if b.suffix.lower() not in extract.SUPPORTED_FORMATS and b.is_file()]
    
    print(f"📂 Found {len(supported)} supported files")
    if unsupported:
        print(f"   ({len(unsupported)} unsupported skipped)")
    
    if not supported:
        print("❌ No supported files to process!")
        return
    
    # Dedup
    print(f"\n🔍 Scanning for duplicates...")
    to_process = dedup_books(supported)
    print(f"   {len(to_process)} unique books to process\n")
    
    # Load embedding model once (reuse for all books)
    print(f"🧠 Loading embedding model ({config.EMBEDDING_MODEL})...")
    embed_model = get_embedding_model()
    print(f"   ✅ Model loaded\n")
    
    # ChromaDB client for unified collection
    chroma_client = get_chroma_client()
    
    # Create or get unified collection
    try:
        unified = chroma_client.get_collection(UNIFIED_COLLECTION)
        existing_count = unified.count()
        print(f"📂 Unified collection '{UNIFIED_COLLECTION}' exists with {existing_count} chunks")
    except Exception:
        unified = chroma_client.create_collection(
            name=UNIFIED_COLLECTION,
            metadata={"description": "Arcwright Storytelling Books RAG — all books combined"}
        )
        print(f"📂 Created unified collection '{UNIFIED_COLLECTION}'")
    
    # Process each book
    results = []
    total_start = time.time()
    
    for i, book_path in enumerate(to_process, 1):
        print(f"\n{'='*50}")
        print(f"  [{i}/{len(to_process)}] Processing: {book_path.name}")
        print(f"{'='*50}")
        
        book_start = time.time()
        book_result = process_single_book(
            book_path, embed_model, chroma_client, unified
        )
        book_time = time.time() - book_start
        
        book_result["time_s"] = round(book_time, 1)
        results.append(book_result)
        
        if book_result["status"] == "completed":
            print(f"  ✅ [{i}/{len(to_process)}] Done in {book_time:.1f}s — {book_result.get('chunks', 0)} chunks")
        else:
            print(f"  ❌ [{i}/{len(to_process)}] FAILED: {book_result.get('error', 'Unknown error')}")
    
    # Summary
    total_time = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  📊 BATCH COMPLETE")
    print(f"{'='*60}")
    
    completed = [r for r in results if r["status"] == "completed"]
    failed = [r for r in results if r["status"] == "error"]
    total_chunks = sum(r.get("chunks", 0) for r in completed)
    
    # Get final unified collection stats
    try:
        final_count = unified.count()
        print(f"\n  ✅ {len(completed)}/{len(to_process)} books processed successfully")
        if failed:
            print(f"  ❌ {len(failed)} books failed: {[f['file'] for f in failed]}")
        print(f"  📚 Total chunks in unified collection: {final_count}")
        print(f"  ⏱️  Total time: {total_time:.1f}s")
        print(f"  🗄️  ChromaDB: {CHROMA_DIR}")
        
        # Per-book summary
        print(f"\n{'='*50}")
        print(f"  📋 PER-BOOK SUMMARY")
        print(f"{'='*50}")
        print(f"  {'Book':<40} {'Chunks':<8} {'Time':<8} {'Status'}")
        print(f"  {'─'*40} {'─'*8} {'─'*8} {'─'*8}")
        for r in completed:
            name = Path(r["file"]).stem[:38]
            print(f"  {name:<40} {r.get('chunks', 0):<8} {r.get('time_s', 0):<8.1f}s ✅")
        for r in failed:
            name = Path(r["file"]).stem[:38]
            print(f"  {name:<40} {'-':<8} {'-':<8} ❌")
    except Exception as e:
        print(f"\n  ⚠️  Error reading final stats: {e}")
    
    # Save batch report
    report = {
        "batch_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_books": len(to_process),
        "completed": len(completed),
        "failed": len(failed),
        "total_chunks": total_chunks,
        "unified_collection": UNIFIED_COLLECTION,
        "chroma_dir": str(CHROMA_DIR),
        "total_time_s": round(total_time, 1),
        "books": [{
            "file": r["file"],
            "collection": r.get("collection", ""),
            "chunks": r.get("chunks", 0),
            "status": r["status"],
            "time_s": r.get("time_s", 0),
            "error": r.get("error"),
        } for r in results],
    }
    
    report_path = OUTPUT_DIR / "batch_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  📄 Batch report: {report_path}")
    print(f"\n{'='*60}")
    print(f"  ✅ ALL DONE — Happy RAG! 🚀")
    print(f"{'='*60}")


def process_single_book(book_path, embed_model, chroma_client, unified_collection):
    """
    Process one book: extract → chunk → save files → add to unified ChromaDB collection.
    """
    result = {
        "file": str(book_path),
        "status": "error",
        "error": None,
        "collection": None,
        "chunks": 0,
    }
    
    try:
        file_name = book_path.stem
        slug = re.sub(r'[^a-zA-Z0-9_]', '_', file_name)[:50]
        
        # Per-book output dir
        book_output = OUTPUT_DIR / slug
        book_output.mkdir(parents=True, exist_ok=True)
        
        # ─── STEP 1: Extract ───
        print(f"  📄 Extracting...")
        markdown = extract.extract_file(str(book_path), force_ocr=True)
        
        md_path = book_output / "extracted.md"
        md_path.write_text(markdown, encoding="utf-8")
        print(f"     Saved: {md_path}")
        
        # ─── STEP 2: Chunk ───
        print(f"  ✂️  Chunking...")
        chunks_list = chunk.chunk_markdown(markdown, source_name=file_name)
        
        chunks_path = book_output / "chunks.json"
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(chunks_list, f, indent=2, ensure_ascii=False)
        
        chunk_stats = chunk.get_chunk_stats(chunks_list)
        print(f"     {chunk_stats['count']} chunks generated")
        print(f"     Saved: {chunks_path}")
        
        if not chunks_list:
            result["error"] = "No chunks generated"
            return result
        
        # ─── STEP 3: Add to unified ChromaDB collection ───
        print(f"  🧠 Embedding & adding to ChromaDB...")
        
        ids = [c["id"] for c in chunks_list]
        texts = [c["text"] for c in chunks_list]
        metadatas = [{
            "title": c["title"][:200],
            "section": c["section"][:200],
            "source": c["source"][:100],
            "book_slug": slug,
            "char_count": str(c["char_count"]),
        } for c in chunks_list]
        
        # Embed in batches
        batch_size = 32
        for i in range(0, len(chunks_list), batch_size):
            batch_end = min(i + batch_size, len(chunks_list))
            batch_texts = texts[i:batch_end]
            batch_ids = ids[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            
            embeddings = embed_model.encode(batch_texts, show_progress_bar=False)
            
            unified_collection.add(
                ids=batch_ids,
                embeddings=embeddings.tolist(),
                documents=batch_texts,
                metadatas=batch_metadatas,
            )
        
        result["status"] = "completed"
        result["collection"] = slug
        result["chunks"] = len(chunks_list)
        
    except Exception as e:
        result["error"] = str(e)
        import traceback
        traceback.print_exc()
    
    return result


# ─── Entry Point ─────────────────────────────────────────────────

if __name__ == "__main__":
    process_all_books()
