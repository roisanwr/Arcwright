"""
Pipeline orchestrator — runs the full extract → chunk → embed pipeline.
Provides high-level functions for API and CLI usage.
"""
import json
import os
import re
import time
import shutil
from pathlib import Path
from typing import Optional

from . import extract, chunk, embed
from . import config


def run_pipeline(
    pdf_path: str,
    collection_name: Optional[str] = None,
    force_ocr: bool = True,
    output_dir: Optional[str] = None,
) -> dict:
    """
    Run the full pipeline: Extract → Chunk → Embed → Store in ChromaDB.
    
    Args:
        pdf_path: Path to the PDF file
        collection_name: Name for ChromaDB collection (default: from filename)
        force_ocr: Whether to force OCR for image-based PDFs
        output_dir: Custom output directory (default: config.OUTPUT_DIR)
    
    Returns:
        Dict with pipeline results:
        - collection: ChromaDB collection name
        - outputs: paths to generated files
        - stats: processing statistics
    """
    pdf_path = str(pdf_path)
    pdf_name = Path(pdf_path).stem
    
    # Clean collection name
    if collection_name is None:
        collection_name = pdf_name.replace(" ", "_").replace("-", "_")
        collection_name = re.sub(r'[^a-zA-Z0-9_]', '', collection_name)[:50]
    
    # Output directory for this PDF's artifacts
    if output_dir:
        pdf_output = Path(output_dir) / collection_name
    else:
        pdf_output = config.OUTPUT_DIR / collection_name
    
    pdf_output.mkdir(parents=True, exist_ok=True)
    
    pipeline_start = time.time()
    results = {
        "collection": collection_name,
        "pdf_name": pdf_name,
        "pdf_path": pdf_path,
        "outputs": {},
        "stats": {},
        "status": "running",
    }
    
    try:
        # ─── Step 1: Extract PDF ───────────────────────────────
        print(f"\n{'='*50}")
        print(f"📄 STEP 1/3: Extracting PDF")
        print(f"{'='*50}")
        
        step_start = time.time()
        markdown = extract.extract_pdf(pdf_path, force_ocr=force_ocr)
        extract_time = time.time() - step_start
        
        md_path = pdf_output / "extracted.md"
        md_path.write_text(markdown, encoding="utf-8")
        
        results["outputs"]["markdown"] = str(md_path)
        results["stats"]["extract"] = {
            "chars": len(markdown),
            "time_s": round(extract_time, 1),
        }
        print(f"  Saved to: {md_path}")
        
        # ─── Step 2: Chunk ─────────────────────────────────────
        print(f"\n{'='*50}")
        print(f"✂️  STEP 2/3: Chunking markdown")
        print(f"{'='*50}")
        
        step_start = time.time()
        chunks = chunk.chunk_markdown(markdown, source_name=pdf_name)
        chunk_time = time.time() - step_start
        
        chunks_path = pdf_output / "chunks.json"
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        
        chunk_stats = chunk.get_chunk_stats(chunks)
        
        results["outputs"]["chunks"] = str(chunks_path)
        results["stats"]["chunk"] = {
            "count": chunk_stats["count"],
            "total_chars": chunk_stats["total_chars"],
            "avg_chars": chunk_stats["avg_chars"],
            "min_chars": chunk_stats["min_chars"],
            "max_chars": chunk_stats["max_chars"],
            "time_s": round(chunk_time, 1),
        }
        print(f"  {chunk_stats['count']} chunks generated")
        print(f"  Avg size: {chunk_stats['avg_chars']} chars")
        print(f"  Saved to: {chunks_path}")
        
        # ─── Step 3: Embed & Store ────────────────────────────
        print(f"\n{'='*50}")
        print(f"🧠 STEP 3/3: Embedding & storing to ChromaDB")
        print(f"{'='*50}")
        
        embed_stats = embed.embed_and_store(chunks, collection_name)
        
        results["outputs"]["chroma_collection"] = collection_name
        results["stats"]["embed"] = embed_stats
        
        # ─── Summary ───────────────────────────────────────────
        total_time = time.time() - pipeline_start
        results["status"] = "completed"
        results["stats"]["total_time_s"] = round(total_time, 1)
        
        print(f"\n{'='*50}")
        print(f"✅ PIPELINE COMPLETE — {total_time:.1f}s")
        print(f"{'='*50}")
        print(f"  Collection : {collection_name}")
        print(f"  Chunks     : {chunk_stats['count']}")
        print(f"  Markdown   : {len(markdown):,} chars")
        print(f"  Downloads  :")
        print(f"    📄 Markdown → {md_path}")
        print(f"    📦 Chunks   → {chunks_path}")
        print(f"    🗄️  ChromaDB → {config.CHROMA_DIR}")
        
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        print(f"\n❌ PIPELINE ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    return results
