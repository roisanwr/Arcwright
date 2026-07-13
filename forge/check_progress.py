#!/usr/bin/env python3
"""Check progress of Arcwright batch RAG processing."""
import os, sys, time, json, subprocess
from pathlib import Path

OUTPUT_DIR = Path(os.path.expanduser("~/Arcwright/forge/output"))
CHROMA_DIR = OUTPUT_DIR / "chroma_db"
REPORT_FILE = OUTPUT_DIR / "batch_report.json"

def get_progress():
    """Check batch process progress."""
    # 1. Is the batch process still running?
    proc_running = False
    try:
        result = subprocess.run(
            ["pgrep", "-f", "batch_process.py"],
            capture_output=True, text=True, timeout=5
        )
        proc_running = bool(result.stdout.strip())
    except:
        pass
    
    # 2. What books have been processed (have output dirs)?
    book_dirs = sorted([d for d in OUTPUT_DIR.iterdir() 
                        if d.is_dir() and d.name != "chroma_db"])
    
    completed_books = []
    for d in book_dirs:
        chunks_file = d / "chunks.json"
        md_file = d / "extracted.md"
        if chunks_file.exists() and md_file.exists():
            try:
                chunks = json.loads(chunks_file.read_text())
                completed_books.append({
                    "name": d.name,
                    "chunks": len(chunks),
                    "size_kb": chunks_file.stat().st_size // 1024,
                })
            except:
                completed_books.append({
                    "name": d.name,
                    "chunks": 0,
                    "size_kb": 0,
                })
    
    # 3. ChromaDB collection stats
    chroma_count = 0
    if CHROMA_DIR.exists():
        try:
            sqlite_file = CHROMA_DIR / "chroma.sqlite3"
            if sqlite_file.exists():
                chroma_size_mb = sqlite_file.stat().st_size // (1024 * 1024)
            # Quick count using chromadb
            sys.path.insert(0, str(Path(os.path.expanduser("~/Arcwright/forge"))))
            import chromadb
            from chromadb.config import Settings
            client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False)
            )
            try:
                col = client.get_collection("storytelling_books")
                chroma_count = col.count()
            except:
                pass
        except:
            chroma_count = -1  # unknown
    else:
        chroma_size_mb = 0
    
    # 4. Read batch report if exists
    total_books = 10  # known from dedup
    if REPORT_FILE.exists():
        try:
            report = json.loads(REPORT_FILE.read_text())
            total_books = report.get("total_books", total_books)
        except:
            pass
    
    return {
        "running": proc_running,
        "completed": len(completed_books),
        "total": total_books,
        "books": completed_books,
        "chroma_chunks": chroma_count,
        "chroma_size_mb": chroma_size_mb if 'chroma_size_mb' in dir() else 0,
        "timestamp": time.strftime("%H:%M:%S"),
    }

progress = get_progress()

# Status
status = "🟢 RUNNING" if progress["running"] else "🔴 STOPPED"
pct = f"{progress['completed']}/{progress['total']}"

# Build output
lines = []
lines.append(f"**📚 Arcwright Batch RAG — {status}**")
lines.append(f"**Progress:** {pct} books completed")
lines.append(f"**ChromaDB:** {progress['chroma_chunks']:,} total chunks")
lines.append("")

if progress["books"]:
    lines.append("**✅ Completed:**")
    for b in progress["books"]:
        lines.append(f"  • {b['name']} — {b['chunks']} chunks ({b['size_kb']}KB)")
    lines.append("")

if progress["running"]:
    remaining = progress["total"] - progress["completed"]
    lines.append(f"⏳ {remaining} book(s) remaining...")
else:
    if progress["completed"] == progress["total"] and progress["completed"] > 0:
        lines.append("🎉 **ALL DONE!** Batch processing complete!")
    else:
        lines.append("⚠️ Process stopped unexpectedly. Check logs.")

print("\n".join(lines))
