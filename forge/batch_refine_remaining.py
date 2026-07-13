#!/usr/bin/env python3
"""Refine 11 remaining books — strictly by exact filename, no dedup."""
import os, sys, time, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# LLM configuration for Contextual Enhancer (Layer 6)
# Default to Ollama local, can be overridden by environment variables
os.environ.setdefault('LLM_API_URL', 'http://localhost:11434/v1')
os.environ.setdefault('LLM_API_KEY', 'ollama')
os.environ.setdefault('LLM_MODEL', 'gemma4:26b')

from arcwright.pipeline import run_pipeline
from arcwright import config
from arcwright.extract import SUPPORTED_FORMATS

STATUS_FILE = config.OUTPUT_DIR / 'batch_refine_remaining.json'
last_notify = time.time()
NOTIFY_INTERVAL = 600

def tg(msg):
    os.system(f'hermes send -t telegram "🔬 Remaining: {msg}" > /dev/null 2>&1')

# The 11 remaining books — exact filenames
REMAINING = [
    "The Science of Storytelling .pdf",
    "The Writers Journey Mythic Structure for Writers, Second Edition (Christopher Vogler) (z-library.sk, 1lib.sk, z-lib.sk).pdf",
    "The Elements of Style, 2011 Revised Edition (William Strunk, Chris Hong) (z-library.sk, 1lib.sk, z-lib.sk).pdf",
    "Steering the Craft A Twenty-First-Century Guide to Sailing the Sea of Story. (Ursula K. Le Guin.) (z-library.sk, 1lib.sk, z-lib.sk).pdf",
    "The Hero with a Thousand Faces Commemorative Edition (Joseph Campbell, Clarissa Pinkola Estes).pdf",
    "The storytellers secret  from TED speakers to business legends, why some ideas catch on and others dont (Gallo, Carmine, author) (z-library.sk, 1lib.sk, z-lib.sk).pdf",
    "Writing Down the Bones. (Natalie Goldberg.) (z-library.sk, 1lib.sk, z-lib.sk).pdf",
    "The Anatomy of Story 22 Steps to Becoming a Master Storyteller (John Truby).pdf",
    "Storytelling with Data (Cole Nussbaumer Knaflic) (z-library.sk, 1lib.sk, z-lib.sk).epub",
    "The Science of Storytelling Why Stories Make Us Human, and How to Tell Them Better (Will Storr).epub",
    "resonate PRESENT VISUAL STORIES THAT TRANSFORM AUDIENCES (Nancy Duarte) (z-library.sk, 1lib.sk, z-lib.sk).epub",
]

# Resolve to actual file paths
BOOKS_DIR = config.BOOKS_DIR
to_process = []
for fname in REMAINING:
    fp = BOOKS_DIR / fname
    if fp.exists():
        to_process.append(fp)
    else:
        print(f"⚠️ NOT FOUND: {fname}")

print(f"Found {len(to_process)}/{len(REMAINING)} books to refine")
print()

# Load previous status if exists
if STATUS_FILE.exists():
    status = json.loads(STATUS_FILE.read_text())
else:
    status = {'processed': [], 'failed': [], 'started_at': time.time()}

done_names = set(p.get('file', '') for p in status.get('processed', []) + status.get('failed', []))
to_process = [p for p in to_process if p.name not in done_names]

def make_col_name(book_path):
    n = book_path.stem
    n = re.sub(r'\([^)]*\)', '', n) if 're' in dir() else n
    import re
    n = re.sub(r'\([^)]*\)', '', n)
    n = re.sub(r'[^a-zA-Z0-9_]', '_', n)[:50]
    return 'refined_' + re.sub(r'_+', '_', n).strip('_').lower()

import re

if not to_process:
    print("🎉 Semua 11 buku udah di-refine sebelumnya!")
    sys.exit(0)

tg(f"Refine {len(to_process)} remaining — GPU batch_size=32")

for idx, book_path in enumerate(to_process):
    col_name = make_col_name(book_path)
    print(f'\n[{idx+1}/{len(to_process)}] {book_path.name}')
    sys.stdout.flush()

    start_t = time.time()
    result = run_pipeline(
        file_path=str(book_path),
        collection_name=col_name,
        force_ocr=False,
        use_boundary=True,
        use_strategy=True,
        use_refiner=True,
        use_enhancer=False,
        skip_embed=True,
    )
    elapsed = time.time() - start_t

    stats = result.get('stats', {})
    cs = stats.get('chunk', {})
    ref = stats.get('refiner', {})
    cl = stats.get('cleanup', {})

    chunks_before = cs.get('count', 0)
    chunks_after = ref.get('chunks_after', chunks_before)

    entry = {
        'file': book_path.name,
        'time_s': round(elapsed, 1),
        'chunks_before': chunks_before,
        'chunks_after': chunks_after,
        'avg_before': cs.get('avg_chars', 0),
        'avg_after': ref.get('avg_chars', 0),
        'cleaned_chars': cl.get('removed_chars', 0),
    }

    if result['status'] == 'completed' and not result.get('error'):
        growth = f'+{((chunks_after-chunks_before)/chunks_before*100):.0f}%' if chunks_before else '?'
        print(f'  ✅ {chunks_before}->{chunks_after} ({growth}) {elapsed:.0f}s')
        status['processed'].append(entry)
    else:
        entry['error'] = result.get('error', 'unknown')
        print(f'  ❌ {entry["error"]}')
        status['failed'].append(entry)

    status['chunks_before'] = sum(p.get('chunks_before', 0) for p in status.get('processed', []))
    status['chunks_after'] = sum(p.get('chunks_after', 0) for p in status.get('processed', []))
    STATUS_FILE.write_text(json.dumps(status, indent=2))

    if time.time() - last_notify >= NOTIFY_INTERVAL:
        done = len(status['processed']) + len(status['failed'])
        tb = status['chunks_before']
        ta = status['chunks_after']
        pct = f'+{((ta-tb)/tb*100):.0f}%' if tb else '?'
        tg(f"Progress {done}/{len(to_process)} — {int((time.time()-status['started_at'])/60)}m\n✅ {len(status['processed'])} sukses\n📊 {tb} -> {ta} ({pct})\n⏳ {book_path.name[:40]}")
        last_notify = time.time()

# Final
tb = status['chunks_before']
ta = status['chunks_after']
pct = f'+{((ta-tb)/tb*100):.0f}%' if tb else '?'
tt = time.time() - status['started_at']
print(f'\n{"="*60}')
print(f'🎉 SELESAI! {len(status["processed"])} remaining books refined')
print(f'📊 {tb} -> {ta} chunks ({pct})')
print(f'⏱ {tt:.0f}s ({tt/60:.1f} min)')
tg(f"SELESAI! {len(status['processed'])} remaining books refined\n📊 {tb} -> {ta} ({pct})\n⏱ {int(tt/60)} menit")
