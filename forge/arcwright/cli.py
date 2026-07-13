#!/usr/bin/env python
"""
arcwright CLI — unified command-line interface for document chunking.

Usage:
    arwright extract file.pdf                            # Extract only
    arwright chunk file.pdf                              # Cleanup + Chunk
    arwright run file.pdf                                # Full pipeline
    arwright run file.pdf --h4 --refine                  # With GPU
    arwright run file.pdf --h4 --refine --enhance        # Full pipeline + LLM
    arwright refine --book "Story" --save                # Refine existing chunks
    arwright stats path/to/output                        # Show chunk stats

Configuration via env vars:
    USE_GPU=True         (or --gpu flag)
    USE_LLM=True         (or --llm flag)
    LLM_API_URL=...
    LLM_API_KEY=...
"""

import sys
import json
import argparse
from pathlib import Path


def main():
    """Main CLI entry point (registered in pyproject.toml)."""
    parser = argparse.ArgumentParser(
        prog="arcwright",
        description="Document chunking engine for RAG pipelines",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    
    # ── run (full pipeline) ────────────────────────────────
    p_run = sub.add_parser("run", help="Run full pipeline on a file")
    p_run.add_argument("file", help="Path to PDF/EPUB/MOBI/DOCX/TXT/HTML")
    p_run.add_argument("--h4", action="store_true", help="Enable H4 boundaries")
    p_run.add_argument("--refine", action="store_true", help="Enable GPU semantic refiner")
    p_run.add_argument("--enhance", action="store_true", help="Enable LLM contextual enhancer")
    p_run.add_argument("--no-boundary", action="store_true", help="Disable boundary detection")
    p_run.add_argument("--no-strategy", action="store_true", help="Disable strategy analyzer")
    p_run.add_argument("--skip-embed", action="store_true", help="Skip embedding step")
    p_run.add_argument("--gpu", action="store_true", help="Enable GPU (sets USE_GPU=True)")
    p_run.add_argument("--llm", action="store_true", help="Enable LLM (sets USE_LLM=True)")
    
    # ── extract ───────────────────────────────────────────
    p_ext = sub.add_parser("extract", help="Extract markdown only")
    p_ext.add_argument("file", help="Path to file")
    
    # ── chunk ─────────────────────────────────────────────
    p_chk = sub.add_parser("chunk", help="Cleanup + chunk only (no embed)")
    p_chk.add_argument("file", help="Path to file")
    p_chk.add_argument("--h4", action="store_true")
    p_chk.add_argument("--no-boundary", action="store_true")
    p_chk.add_argument("--gpu", action="store_true")
    
    # ── refine ────────────────────────────────────────────
    p_ref = sub.add_parser("refine", help="Refine existing chunks with GPU")
    p_ref.add_argument("--book", help="Refine only matching book")
    p_ref.add_argument("--chunks", help="Path to specific chunks.json")
    p_ref.add_argument("--save", action="store_true", help="Save refined chunks")
    p_ref.add_argument("--split-threshold", type=float, default=0.7)
    p_ref.add_argument("--device", default="auto", help="cuda / cpu / auto")
    
    # ── stats ─────────────────────────────────────────────
    p_st = sub.add_parser("stats", help="Show chunk statistics for output")
    p_st.add_argument("path", nargs="?", default=".", help="Output path or book folder")
    
    # ── version ───────────────────────────────────────────
    sub.add_parser("version", help="Show version info")
    
    args = parser.parse_args()
    
    # Route to handler
    if args.command == "version":
        _cmd_version()
    elif args.command == "extract":
        _cmd_extract(args)
    elif args.command == "chunk":
        _cmd_chunk(args)
    elif args.command == "run":
        _cmd_run(args)
    elif args.command == "refine":
        _cmd_refine(args)
    elif args.command == "stats":
        _cmd_stats(args)


# ─── Command Handlers ──────────────────────────────────

def _cmd_version():
    print("arcwright-forge v2.0.0")
    print("Multi-strategy document chunking engine")


def _cmd_extract(args):
    """Extract markdown only."""
    file_path = str(args.file)
    print("  📄 Extracting:", file_path)
    
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from arcwright import extract
    from arcwright import config
    
    markdown = extract.extract_file(file_path)
    out = Path(file_path).stem + "_extracted.md"
    Path(out).write_text(markdown, encoding="utf-8")
    print(f"  ✅ Saved to: {out} ({len(markdown):,} chars)")


def _cmd_chunk(args):
    """Cleanup + chunk (no embed)."""
    _apply_flags(args)
    file_path = str(args.file)
    
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from arcwright import pipeline
    
    result = pipeline.run_pipeline(
        file_path,
        use_h4=args.h4,
        use_boundary=not args.no_boundary,
        use_strategy=True,
        skip_embed=True,
    )
    _print_result(result)


def _cmd_run(args):
    """Full pipeline."""
    _apply_flags(args)
    file_path = str(args.file)
    
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from arcwright import pipeline
    
    result = pipeline.run_pipeline(
        file_path,
        use_h4=args.h4,
        use_refiner=args.refine,
        use_enhancer=args.enhance,
        use_boundary=not args.no_boundary,
        use_strategy=not args.no_strategy,
        skip_embed=args.skip_embed,
    )
    _print_result(result)


def _cmd_refine(args):
    """Refine existing chunks with GPU."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from arcwright.refiner import SemanticRefiner
    from arcwright import chunk
    from arcwright import config as cfg
    
    cfg.USE_GPU = True  # Force GPU for refine
    
    refiner = SemanticRefiner(device=args.device)
    
    if args.chunks:
        paths = [Path(args.chunks)]
    else:
        output_dir = Path(__file__).resolve().parent.parent / "output"
        paths = sorted(output_dir.glob("*/chunks.json"))
        if args.book:
            paths = [p for p in paths if args.book.lower() in p.parent.name.lower()]
    
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        before = len(data)
        refined = refiner.refine_all(data, split_threshold=args.split_threshold)
        after = len(refined)
        print(f"  {p.parent.name}: {before} → {after} chunks")
        
        if args.save:
            out = p.parent / "chunks_refined.json"
            out.write_text(json.dumps(refined, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"    💾 Saved to: {out}")


def _cmd_stats(args):
    """Show chunk statistics."""
    base = Path(args.path)
    
    if not base.exists():
        print(f"  ❌ Path not found: {base}")
        return
    
    # Find all chunks.json files
    if base.is_file() and base.name == "chunks.json":
        paths = [base]
    elif base.is_dir():
        paths = sorted(base.glob("*/chunks.json"))
        if not paths:
            paths = [base / "chunks.json"] if (base / "chunks.json").exists() else []
    else:
        paths = []
    
    if not paths:
        print("  ❌ No chunks.json found")
        return
    
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from arcwright import chunk
    
    total_chunks = 0
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        st = chunk.get_chunk_stats(data)
        total_chunks += st["count"]
        name = p.parent.name[:50]
        print(f"  {name:<50} {st['count']:>5} chunks  "
              f"avg={st['avg_chars']}  [{st['min_chars']}–{st['max_chars']}]  "
              f"flagged={st['refiner_needed']}")
    
    print(f"\n  Total: {total_chunks} chunks across {len(paths)} files")


# ─── Helpers ─────────────────────────────────────────

def _apply_flags(args):
    """Apply CLI flags to config."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from arcwright import config
    
    if getattr(args, "gpu", False):
        config.USE_GPU = True
        print("  ⚡ GPU mode enabled")
    if getattr(args, "llm", False):
        config.USE_LLM = True
        print("  🧠 LLM mode enabled")


def _print_result(result: dict):
    """Pretty-print pipeline result."""
    status = result.get("status", "unknown")
    print(f"\n  ✅ Status: {status}")
    if "stats" in result:
        s = result["stats"]
        if "extract" in s:
            print(f"  📄 Extract:  {s['extract']['chars']:,} chars ({s['extract']['time_s']}s)")
        if "cleanup" in s:
            print(f"  🧹 Cleanup:  {s['cleanup'].get('removed_pct', 0)}% artifacts removed")
        if "chunk" in s:
            print(f"  ✂️  Chunks:   {s['chunk']['count']} ({s['chunk'].get('flagged_pct', 0)}% flagged)")
        if "strategy" in s and s['strategy'] != {"skipped": True}:
            print(f"  🧠 Strategy: {s['strategy'].get('strategy', '-')} ({s['strategy'].get('source', '-')})")
        if "refiner" in s and s['refiner'] != {"skipped": True}:
            print(f"  🎯 Refined:  {s['refiner'].get('chunks_after', '-')} chunks")
        if "enhancer" in s and s['enhancer'] != {"skipped": True}:
            print(f"  🌟 Enhanced: {s['enhancer'].get('enhanced', '-')} chunks")
    if "error" in result:
        print(f"  ❌ Error: {result['error']}")


if __name__ == "__main__":
    main()
