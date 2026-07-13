"""
Pipeline orchestrator — runs the full extract → cleanup → chunk → embed pipeline.
Now supports: PDF, EPUB, MOBI, DOCX, TXT, HTML.
Provides high-level functions for API and CLI usage.
"""

import json
import os
import re
import time
import shutil
from pathlib import Path
from typing import Optional

from . import extract, cleanup, chunk
from . import config


def run_pipeline(
    file_path: str,
    collection_name: Optional[str] = None,
    force_ocr: bool = True,
    output_dir: Optional[str] = None,
    use_h4: bool = False,
    heading_levels: list = None,
    min_chars: int = None,
    max_chars: int = None,
    skip_embed: bool = False,
    use_refiner: bool = False,
    use_strategy: bool = True,
    use_enhancer: bool = False,
) -> dict:
    """
    Run the full pipeline: Extract → Cleanup → Analyze → Chunk → Refine → Enhance → Embed.

    Supports: PDF, EPUB, MOBI, AZW3, DOCX, TXT, HTML

    Args:
        file_path: Path to the file
        collection_name: Name for ChromaDB collection (default: from filename)
        force_ocr: Only for PDF — force OCR for image-based PDFs
        output_dir: Custom output directory (default: config.OUTPUT_DIR)
        use_h4: Treat H4 headings as chunk boundaries
        heading_levels: Custom heading levels for chunking
        min_chars: Minimum chars per chunk
        max_chars: Maximum chars before flagging for semantic refiner
        skip_embed: If True, stop after chunking (don't embed or store)
        use_refiner: If True, run GPU semantic refiner on flagged chunks
        use_strategy: If True, run strategy analyzer before chunking
        use_enhancer: If True, run LLM contextual enhancer on chunks

    Returns:
        Dict with pipeline results
    """
    file_path = str(file_path)
    path = Path(file_path)
    file_name = path.stem
    file_ext = path.suffix.lower()

    if not path.exists():
        return {
            "status": "error",
            "error": f"File not found: {file_path}",
        }

    # Detect format
    fmt = extract.detect_format(file_path)
    print(f"\n{'='*60}")
    print(f"  📂 File: {path.name}")
    print(f"  📋 Format: {fmt}")
    if use_h4:
        print(f"  🏷️  H4 boundaries: ENABLED")
    if heading_levels:
        print(f"  🏷️  Heading levels: H{','.join(str(h) for h in heading_levels)}")
    print(f"{'='*60}")

    # Clean collection name
    if collection_name is None:
        collection_name = file_name.replace(" ", "_").replace("-", "_")
        collection_name = re.sub(r'[^a-zA-Z0-9_]', '', collection_name)[:50]

    # Output directory for this file's artifacts
    if output_dir:
        file_output = Path(output_dir) / collection_name
    else:
        file_output = config.OUTPUT_DIR / collection_name

    file_output.mkdir(parents=True, exist_ok=True)

    pipeline_start = time.time()
    results = {
        "collection": collection_name,
        "file_name": file_name,
        "file_path": file_path,
        "format": fmt,
        "outputs": {},
        "stats": {},
        "status": "running",
    }

    try:
        # ─── Step 1: Extract ───────────────────────────────────
        print(f"\n{'='*50}")
        print(f"📄 STEP 1/7: Extracting content")
        print(f"{'='*50}")

        step_start = time.time()
        markdown = extract.extract_file(file_path, force_ocr=force_ocr)
        extract_time = time.time() - step_start

        md_path = file_output / "extracted.md"
        md_path.write_text(markdown, encoding="utf-8")

        results["outputs"]["markdown"] = str(md_path)
        results["stats"]["extract"] = {
            "chars": len(markdown),
            "time_s": round(extract_time, 1),
        }
        print(f"  Extracted: {len(markdown):,} chars in {extract_time:.1f}s")
        print(f"  Saved to: {md_path}")

        # ─── Step 2: Cleanup ────────────────────────────────────
        print(f"\n{'='*50}")
        print(f"🧹 STEP 2/7: Cleaning markdown")
        print(f"{'='*50}")

        step_start = time.time()
        cleaned = cleanup.clean_markdown(markdown)
        cleanup_time = time.time() - step_start

        clean_stats = cleanup.get_cleanup_stats(markdown, cleaned)
        results["stats"]["cleanup"] = {
            **clean_stats,
            "time_s": round(cleanup_time, 1),
        }
        print(f"  Removed: {clean_stats['removed_chars']:,} chars "
              f"({clean_stats['removed_pct']}%)")
        print(f"  Lines: {clean_stats['original_lines']} → {clean_stats['cleaned_lines']}")

        # Save cleaned version
        clean_path = file_output / "cleaned.md"
        clean_path.write_text(cleaned, encoding="utf-8")
        results["outputs"]["cleaned"] = str(clean_path)
        print(f"  Saved to: {clean_path}")

        # ─── Step 2.5: Strategy Analysis (optional) ────────────
        strategy_config = {}
        if use_strategy:
            print(f"\n{'='*50}")
            print(f"🧠 STEP 2.5/7: Analyzing structure & strategy")
            print(f"{'='*50}")

            from . import strategy
            strategy_config = strategy.detect_and_configure(
                cleaned, source_name=file_name
            )
            print(strategy.format_report(strategy_config))

            # Apply strategy findings (unless user explicitly overrode)
            if not use_h4 and strategy_config.get("use_h4"):
                use_h4 = True
                print(f"  → Auto-enabled H4 boundaries (recommended)")
            if heading_levels is None and strategy_config.get("heading_levels"):
                heading_levels = strategy_config["heading_levels"]
            if min_chars is None and strategy_config.get("chunk_size_min"):
                min_chars = strategy_config["chunk_size_min"]
            if max_chars is None and strategy_config.get("chunk_size_max"):
                max_chars = strategy_config["chunk_size_max"]

            results["stats"]["strategy"] = {
                "source": strategy_config.get("_source", "offline"),
                "strategy": strategy_config.get("strategy", "heading_based"),
                "book_type": strategy_config.get("book_type", "unknown"),
                "use_h4": use_h4,
            }
        else:
            results["stats"]["strategy"] = {"skipped": True}

        # ─── Step 3: Chunk ─────────────────────────────────────
        print(f"\n{'='*50}")
        print(f"✂️  STEP 3/7: Chunking content")
        print(f"{'='*50}")

        step_start = time.time()
        chunks_list = chunk.chunk_markdown(
            cleaned,
            source_name=file_name,
            heading_levels=heading_levels,
            min_chars=min_chars,
            max_chars=max_chars,
            use_h4=use_h4,
        )
        chunk_time = time.time() - step_start

        chunks_path = file_output / "chunks.json"
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(chunks_list, f, indent=2, ensure_ascii=False)

        chunk_stats = chunk.get_chunk_stats(chunks_list)

        results["outputs"]["chunks"] = str(chunks_path)
        results["stats"]["chunk"] = {
            "count": chunk_stats["count"],
            "total_chars": chunk_stats["total_chars"],
            "avg_chars": chunk_stats["avg_chars"],
            "min_chars": chunk_stats["min_chars"],
            "max_chars": chunk_stats["max_chars"],
            "refiner_needed": chunk_stats["refiner_needed"],
            "flagged_pct": chunk_stats["flagged_pct"],
            "time_s": round(chunk_time, 1),
        }
        print(f"  {chunk_stats['count']} chunks generated")
        print(f"  Avg size: {chunk_stats['avg_chars']} chars")
        print(f"  Range: {chunk_stats['min_chars']} – {chunk_stats['max_chars']} chars")
        if chunk_stats["refiner_needed"] > 0:
            print(f"  ⚠️  {chunk_stats['refiner_needed']} chunks flagged for semantic refiner")
        print(f"  Saved to: {chunks_path}")

        # ─── Step 3.5: Semantic Refinement (optional) ─────────
        if use_refiner:
            print(f"\n{'='*50}")
            print(f"🎯 STEP 3.5/7: Semantic refinement (GPU)")
            print(f"{'='*50}")

            if not config.USE_GPU:
                print(f"  ⚠️  USE_GPU=False in config — forcing GPU mode for this run")
                # Temporarily enable for this pipeline call

            from . import refiner as refiner_module
            ref = refiner_module.SemanticRefiner(device="auto")
            chunks_list = ref.refine_all(chunks_list)

            # Recalculate stats after refinement
            chunk_stats = chunk.get_chunk_stats(chunks_list)

            # Save refined chunks
            refine_path = file_output / "chunks_refined.json"
            with open(refine_path, "w", encoding="utf-8") as f:
                json.dump(chunks_list, f, indent=2, ensure_ascii=False)
            results["outputs"]["chunks_refined"] = str(refine_path)
            results["stats"]["refiner"] = {
                "chunks_after": chunk_stats["count"],
                "avg_chars": chunk_stats["avg_chars"],
                "min_chars": chunk_stats["min_chars"],
                "max_chars": chunk_stats["max_chars"],
            }
            print(f"  Saved refined chunks to: {refine_path}")
        else:
            results["stats"]["refiner"] = {"skipped": True}

        # ─── Step 3.75: Contextual Enhancement (optional) ───────
        if use_enhancer:
            print(f"\n{'='*50}")
            print(f"🌟 STEP 3.75/7: Contextual enhancement (LLM)")
            print(f"{'='*50}")

            from . import enhancer
            enh = enhancer.ContextualEnhancer(
                batch_size=config.ENHANCER_BATCH_SIZE
            )
            chunks_list = enh.enhance_all(chunks_list, cleaned)

            # Save enhanced chunks
            enhance_path = file_output / "chunks_enhanced.json"
            with open(enhance_path, "w", encoding="utf-8") as f:
                json.dump(chunks_list, f, indent=2, ensure_ascii=False)

            enh_stats = enhancer.ContextualEnhancer.get_enhancer_stats(
                chunks_list, chunks_list
            )
            results["outputs"]["chunks_enhanced"] = str(enhance_path)
            results["stats"]["enhancer"] = {
                "enhanced": enh_stats["enhanced"],
                "enhanced_pct": enh_stats["enhanced_pct"],
                "avg_context_len": enh_stats["avg_context_len"],
            }
            print(f"  Saved enhanced chunks to: {enhance_path}")
        else:
            results["stats"]["enhancer"] = {"skipped": True}

        # ─── Step 4: Embed & Store (optional) ─────────────────
        if not skip_embed:
            print(f"\n{'='*50}")
            print(f"🧠 STEP 4/7: Embedding & storing to ChromaDB")
            print(f"{'='*50}")

            from . import embed
            embed_stats = embed.embed_and_store(chunks_list, collection_name)

            results["outputs"]["chroma_collection"] = collection_name
            results["stats"]["embed"] = embed_stats
        else:
            print(f"\n{'='*50}")
            print(f"⏭️  STEP 5/7: Skipped (skip_embed=True)")
            print(f"{'='*50}")
            results["stats"]["embed"] = {"skipped": True}

        # ─── Summary ───────────────────────────────────────────
        total_time = time.time() - pipeline_start
        results["status"] = "completed"
        results["stats"]["total_time_s"] = round(total_time, 1)

        print(f"\n{'='*50}")
        print(f"✅ PIPELINE COMPLETE — {total_time:.1f}s")
        print(f"{'='*50}")
        print(f"  Format    : {fmt}")
        print(f"  Collection: {collection_name}")
        print(f"  Chunks    : {chunk_stats['count']}")
        print(f"  Cleaned   : {clean_stats['cleaned_chars']:,} chars")
        if clean_stats["removed_chars"] > 0:
            print(f"  Artifacts : {clean_stats['removed_chars']:,} chars removed")
        if chunk_stats["refiner_needed"] > 0:
            print(f"  ⚠️  {chunk_stats['refiner_needed']} chunks > {config.CHUNK_MAX_CHARS} chars")
            print(f"     → Run semantic refiner (Layer 5) on GPU machine")
        print(f"  Files     :")
        print(f"    📄 Markdown → {md_path}")
        print(f"    🧹 Cleaned  → {clean_path}")
        print(f"    📦 Chunks   → {chunks_path}")
        if not skip_embed:
            print(f"    🗄️  ChromaDB → {config.CHROMA_DIR}")

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        print(f"\n❌ PIPELINE ERROR: {e}")
        import traceback
        traceback.print_exc()

    return results
