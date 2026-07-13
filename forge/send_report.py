#!/usr/bin/env python3
"""Generate and send final comparison report to Telegram."""
import json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

output_dir = Path('output')

# Collect all data
refined_dirs = sorted([d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith('refined_')])

# Map: get old chunks for each refined book
def norm(name):
    import re
    n = re.sub(r'\([^)]*\)', '', name)
    n = re.sub(r'[:\\-–—].*$', '', n)
    n = re.sub(r'\b(the|a|an|of|and|by|for|in|to)\b', ' ', n, flags=re.I)
    n = re.sub(r'\s+', ' ', n).strip().lower()
    return n

# Load old dirs
old_dirs = {}
for d in output_dir.iterdir():
    if d.is_dir() and d.name != 'chroma_db':
        if not any(d.name.startswith(p) for p in ['rechunk_','refined_','compare_','6layer_','full6layer_','test_']):
            cf = d / 'chunks.json'
            if cf.exists():
                with open(cf) as f:
                    c = json.load(f)
                if isinstance(c, list) and len(c) > 0 and 'text' in c[0]:
                    old_dirs[d.name.lower()] = c

rows = []
total_old = 0
total_new = 0

for d in refined_dirs:
    cf = d / 'chunks.json'
    rf = d / 'chunks_refined.json'
    if not (cf.exists() and rf.exists()):
        continue
    with open(cf) as f: before = json.load(f)
    with open(rf) as f: after = json.load(f)
    
    bc = len(before)
    ac = len(after)
    
    # Find old chunks for comparison
    slug = d.name.replace('refined_','').lower()
    old_chunks_count = 0
    for od_name, od_chunks in old_dirs.items():
        if slug[:20] in od_name or od_name[:20] in slug:
            old_chunks_count = len(od_chunks)
            break
    
    bsize = sum(c['char_count'] for c in before)//bc if bc else 0
    asize = sum(c['char_count'] for c in after)//ac if ac else 0
    
    rows.append({
        'name': d.name.replace('refined_','')[:30],
        'old_chunks': old_chunks_count or bc,
        'new_chunks': ac,
        'old_avg': bsize,
        'new_avg': asize,
        'growth': f'+{((ac-(old_chunks_count or bc))/(old_chunks_count or bc)*100):.0f}%' if (old_chunks_count or bc) else '?',
        'growth_num': ((ac-(old_chunks_count or bc))/(old_chunks_count or bc))*100 if (old_chunks_count or bc) else 0,
    })
    total_old += old_chunks_count or bc
    total_new += ac

# Sort by growth descending
rows.sort(key=lambda r: r['growth_num'], reverse=True)

# Build message
lines = []
lines.append("📊 ARCRIGHT — BEFORE vs AFTER GPU REFINER")
lines.append(f"Total: {len(rows)} books | Old: {total_old} → New: {total_new} chunks")
lines.append(f"Growth: +{((total_new/total_old)-1)*100:.0f}%")
lines.append("")
lines.append(f"```")
lines.append(f"{'Book':<30} {'Old':>5} {'New':>5} {'Growth':>8} {'Avg Old':>7} {'Avg New':>7}")
lines.append(f"{'-'*62}")
for r in rows:
    lines.append(f"{r['name']:<30} {r['old_chunks']:>5} {r['new_chunks']:>5} {r['growth']:>8} {r['old_avg']:>7} {r['new_avg']:>7}")
lines.append(f"{'-'*62}")
lines.append(f"{'TOTAL':<30} {total_old:>5} {total_new:>5} {'+'+f'{((total_new/total_old)-1)*100:.0f}%':>8}")
lines.append(f"```")
lines.append("")
lines.append("🏆 Top Growth:")
# top 3 by growth
for r in rows[:3]:
    lines.append(f"  • {r['name'][:25]} — {r['growth']} (Old: {r['old_chunks']} → New: {r['new_chunks']})")
lines.append("")
lines.append("📉 Min Growth:")
for r in rows[-3:]:
    lines.append(f"  • {r['name'][:25]} — {r['growth']}")
lines.append("")
lines.append("⚡ Next: Layer 6 (LLM Enhancer) with Gemma 4:26b local")

msg = "\n".join(lines)

# Save to file for sending
with open('/tmp/arcwright_report.txt', 'w') as f:
    f.write(msg)

# Print to console
print(msg)

# Send via hermes send
import subprocess
subprocess.run(['hermes', 'send', '-t', 'telegram', '-f', '/tmp/arcwright_report.txt'], capture_output=True)
print("\n✅ Report sent to Telegram!")
