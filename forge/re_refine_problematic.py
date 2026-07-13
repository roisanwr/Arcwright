#!/usr/bin/env python3
"""Re-refine oversized chunks with force-split @ 2000 chars.
Loads chunks.json (original L3) from each refined folder, runs the refiner,
and overwrites chunks_refined.json with tighter chunks."""
import os, sys, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arcwright import config
from arcwright.refiner import SemanticRefiner

BASE = config.OUTPUT_DIR

# Find all refined folders
refined = sorted([d for d in BASE.iterdir() if d.is_dir() and d.name.startswith('refined_')])

print(f"🔍 Scanning {len(refined)} refined folders...\n")

candidates = []
for d in refined:
    chunks_path = d / 'chunks.json'
    if not chunks_path.exists():
        print(f"  ⏭️  {d.name}: no chunks.json found")
        continue
    with open(chunks_path) as f:
        chunks = json.load(f)
    chars = [len(c.get('text','')) for c in chunks]
    avg = sum(chars)/len(chars) if chars else 0
    over_2k = sum(1 for c in chars if c > 2000)
    
    status = "✅" if over_2k == 0 else f"⚠️ {over_2k}x >2k"
    print(f"  {status} {d.name[:50]:50s} avg={avg:5.0f} | total={len(chunks):4d}")
    
    if over_2k > 0:
        candidates.append((d, chunks))

if not candidates:
    print("\n✅ Semua buku gak perlu re-refine!")
    sys.exit(0)

print(f"\n🎯 {len(candidates)} folders butuh re-refine")
print(f"🔥 Initializing BGE-M3 refiner on GPU...\n")

refiner = SemanticRefiner(device="auto")

total_before = 0
total_after = 0
t_start = time.time()

for d, chunks in candidates:
    n_before = len(chunks)
    chars_before = [len(c.get('text','')) for c in chunks]
    over2k_before = sum(1 for c in chars_before if c > 2000)
    over2k_before_1500 = sum(1 for c in chars_before if c > 1500)
    
    print(f"\n{'='*60}")
    print(f"📖 {d.name}")
    chars_avg_before = sum(chars_before)/len(chars_before) if chars_before else 0
    print(f"   Before: {n_before} chunks | avg {chars_avg_before:.0f} | >1500={over2k_before_1500} | >2000={over2k_before}")
    print(f"{'='*60}")
    
    t0 = time.time()
    refined_chunks = refiner.refine_all(chunks)
    elapsed = time.time() - t0
    n_after = len(refined_chunks)
    total_before += n_before
    total_after += n_after
    
    # Stats
    new_chars = [len(c.get('text','')) for c in refined_chunks]
    new_avg = sum(new_chars)/len(new_chars) if new_chars else 0
    over2k_after = sum(1 for c in new_chars if c > 2000)
    over2k_after_1500 = sum(1 for c in new_chars if c > 1500)
    still_over = sum(1 for c in new_chars if c > config.CHUNK_HARD_MAX_CHARS)
    
    # Save
    if (d / 'chunks_refined.json').exists():
        bak = d / 'chunks_refined.json.bak'
        if not bak.exists():
            os.rename(d / 'chunks_refined.json', bak)
    out_path = d / 'chunks_refined.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(refined_chunks, f, indent=2, ensure_ascii=False)
    
    print(f"   After:  {n_after} chunks | avg {new_avg:.0f} | >1500={over2k_after_1500} | >2000={over2k_after}")
    print(f"   Delta:  {'+' if n_after>=n_before else ''}{n_after-n_before} chunks ({elapsed:.0f}s)")
    if still_over > 0:
        print(f"   ❌ {still_over} chunk masih > {config.CHUNK_HARD_MAX_CHARS} chars!")
    else:
        print(f"   ✅ Semua chunk ≤ {config.CHUNK_HARD_MAX_CHARS} chars!")

total_time = time.time() - t_start
print(f"\n{'='*60}")
print(f"✅ ALL DONE — {total_time:.0f}s")
print(f"📊 Total: {total_before} → {total_after} chunks (+{(total_after-total_before)/total_before*100:.0f}%)")
print(f"{'='*60}")
