#!/usr/bin/env python
"""
Run GPU semantic refinement on existing chunks.json files.

Usage:
    python scripts/run-refine.py                                    # All books in output/
    python scripts/run-refine.py --book "Story Genius"             # Specific book
    python scripts/run-refine.py --chunks path/to/chunks.json      # Single file
    python scripts/run-refine.py --split-threshold 0.65 --save     # Custom threshold
"""

import json
import sys
import argparse
from pathlib import Path

# Ensure forge/ is on the path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from arcwright.refiner import SemanticRefiner
from arcwright import chunk


def refine_file(chunks_path: Path, refiner: SemanticRefiner, 
                split_threshold: float, merge_threshold: float,
                save: bool = False) -> list:
    """Refine a single chunks.json file."""
    print(f"\n  📄 {chunks_path.parent.name}")
    
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks_list = json.load(f)
    
    before = len(chunks_list)
    stats_before = chunk.get_chunk_stats(chunks_list)
    flagged = stats_before["refiner_needed"]
    
    print(f"     Before: {before} chunks ({flagged} flagged for split)")
    
    if flagged == 0:
        print(f"     ⏭️  No refinement needed")
        return chunks_list
    
    # Run refiner
    refined = refiner.refine_all(
        chunks_list,
        split_threshold=split_threshold,
        merge_threshold=merge_threshold,
    )
    
    after = len(refined)
    stats_after = chunk.get_chunk_stats(refined)
    
    print(f"     After:  {after} chunks (avg {stats_after['avg_chars']} chars)")
    print(f"     Δ: {before} → {after} ({'+' if after > before else ''}{after - before})")
    
    if save:
        out_path = chunks_path.parent / "chunks_refined.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(refined, f, indent=2, ensure_ascii=False)
        print(f"     💾 Saved to: {out_path}")
    
    return refined


def main():
    parser = argparse.ArgumentParser(description="GPU semantic refiner for chunks")
    parser.add_argument("--chunks", help="Path to a single chunks.json file")
    parser.add_argument("--book", help="Refine only this book (substring match)")
    parser.add_argument("--split-threshold", type=float, default=0.7,
                        help="Cosine sim threshold for topic shift (default: 0.7)")
    parser.add_argument("--merge-threshold", type=float, default=0.95,
                        help="Cosine sim threshold for merge (default: 0.95)")
    parser.add_argument("--save", action="store_true",
                        help="Save refined chunks to chunks_refined.json")
    parser.add_argument("--device", default="auto",
                        help="Device: 'cuda', 'cpu', or 'auto' (default)")
    
    args = parser.parse_args()
    
    # ── Init refiner (loads BGE-M3 on GPU) ─────────────────
    print("=" * 60)
    print("  🔥 Semantic Refiner — Phase 2")
    print("=" * 60)
    refiner = SemanticRefiner(device=args.device)
    
    # ── Collect chunks files ──────────────────────────────
    if args.chunks:
        paths = [Path(args.chunks)]
    else:
        output_dir = project_root / "output"
        paths = sorted(output_dir.glob("*/chunks.json"))
        if args.book:
            paths = [p for p in paths if args.book.lower() in p.parent.name.lower()]
    
    if not paths:
        print("  ❌ No chunks.json files found")
        sys.exit(1)
    
    print(f"\n  Found {len(paths)} file(s) to process")
    
    # ── Process each ──────────────────────────────────────
    for p in paths:
        refine_file(p, refiner, args.split_threshold, args.merge_threshold, args.save)
    
    print(f"\n{'='*60}")
    print(f"  ✅ Done — {len(paths)} file(s) processed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
