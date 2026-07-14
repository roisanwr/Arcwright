#!/usr/bin/env python3
import os, sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from arcwright import config
from arcwright.refiner import SemanticRefiner

BASE = config.OUTPUT_DIR
targets = [
    'refined_power_of_myth',
    'refined_story_genius',
    'refined_storyworthy',
    'refined_truth_in_comedy',
]

refiner = SemanticRefiner(device="auto")

for d in targets:
    fp = os.path.join(BASE, d, 'chunks.json')
    with open(fp) as f:
        chunks = json.load(f)
    
    chars = [len(c.get('text','')) for c in chunks]
    n_before = len(chunks)
    avg_before = sum(chars)/len(chars)
    o2k = sum(1 for c in chars if c > 2000)
    print(f'\n=== {d} ===')
    print(f'Before: {n_before} chunks, avg {avg_before:.0f}, >2000={o2k}')
    
    t0 = time.time()
    refined = refiner.refine_all(chunks)
    elapsed = time.time() - t0
    
    new_chars = [len(c.get('text','')) for c in refined]
    n_after = len(refined)
    avg_after = sum(new_chars)/len(new_chars)
    o2k_a = sum(1 for c in new_chars if c > 2000)
    still_over = sum(1 for c in new_chars if c > config.CHUNK_HARD_MAX_CHARS)
    
    out = os.path.join(BASE, d, 'chunks_refined.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(refined, f, indent=2, ensure_ascii=False)
    
    print(f'After:  {n_after} chunks, avg {avg_after:.0f}, >2000={o2k_a}, >{config.CHUNK_HARD_MAX_CHARS}={still_over}')
    print(f'Time:   {elapsed:.0f}s')
    print(f'Status: {"✅ ALL OK" if still_over == 0 else f"⚠️ {still_over} masih bocor"}')

print('\n✅ DONE')
