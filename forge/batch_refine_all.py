#!/usr/bin/env python3
"""Batch refine all old-chunk books through Layer 5 GPU Refiner + notify Telegram every 10 min."""
import os, sys, time, json, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ['LLM_API_URL'] = 'https://opencode.ai/zen/v1'
os.environ['LLM_API_KEY'] = 'public'
os.environ['LLM_MODEL'] = 'deepseek-v4-flash-free'

from arcwright.pipeline import run_pipeline
from arcwright import config
from arcwright.extract import SUPPORTED_FORMATS

STATUS_FILE = config.OUTPUT_DIR / 'batch_refine_status.json'
last_notify = time.time()
NOTIFY_INTERVAL = 600  # 10 minutes

def tg(msg):
    os.system(f'hermes send -t telegram "🔬 Arcwright: {msg}" > /dev/null 2>&1')

def load_status():
    if STATUS_FILE.exists():
        with open(STATUS_FILE) as f:
            return json.load(f)
    return {'processed': [], 'failed': [], 'current': None, 'started_at': time.time(),
            'books_total': 0, 'chunks_before': 0, 'chunks_after': 0, 'batch': 1}

def save_status(s):
    with open(STATUS_FILE, 'w') as f:
        json.dump(s, f, indent=2)

def normalize(name):
    n = re.sub(r'\([^)]*\)', '', name)
    n = re.sub(r'[:\\-–—].*$', '', n)
    n = re.sub(r'\b(the|a|an|of|and|by|for|in|to)\b', ' ', n, flags=re.I)
    n = re.sub(r'\s+', ' ', n).strip().lower()
    return n

def make_slug(book_path):
    n = book_path.stem
    n = re.sub(r'\([^)]*\)', '', n)
    n = re.sub(r'[^a-zA-Z0-9_]', '_', n)[:50]
    return re.sub(r'_+', '_', n).strip('_').lower()

# Load all books
all_books = sorted(config.BOOKS_DIR.glob('*'))
supported = [b for b in all_books if b.suffix.lower() in SUPPORTED_FORMATS]

# Dedup
groups = {}
for b in supported:
    norm = normalize(b.name)
    groups.setdefault(norm, []).append(b)

FORMAT_PREF = ['.pdf', '.epub', '.mobi', '.azw3', '.docx', '.txt', '.html']
unique_books = []
for norm, versions in groups.items():
    versions.sort(key=lambda v: FORMAT_PREF.index(v.suffix.lower()) if v.suffix.lower() in FORMAT_PREF else 99)
    unique_books.append(versions[0])

# Filter: books with old chunks (not refined/rechunk/compare)
existing_slugs = set()
for d in config.OUTPUT_DIR.iterdir():
    if d.is_dir() and d.name != 'chroma_db':
        if not any(d.name.startswith(p) for p in ['rechunk_', 'refined_', 'compare_', '6layer_', 'full6layer_', 'test_']):
            existing_slugs.add(d.name.lower())

to_process = []
for book_path in unique_books:
    slug = make_slug(book_path)
    for es in existing_slugs:
        if slug[:20] in es or es[:20] in slug:
            to_process.append(book_path)
            break

status = load_status()
done_names = set(p.get('file', '') for p in status.get('processed', []) + status.get('failed', []))
to_process = [b for b in to_process if b.name not in done_names]

status['books_total'] = len(to_process)
status['started_at'] = time.time()
save_status(status)

tg(f"Mulai refine {len(to_process)} buku GPU — Batch {status.get('batch', 1)}")
print(f"🧪 Akan memproses {len(to_process)} buku dengan GPU batch_size=32")

for idx, book_path in enumerate(to_process):
    col_name = f'refined_{make_slug(book_path)}'[:50]
    status['current'] = book_path.name
    save_status(status)

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

    entry = {
        'file': book_path.name,
        'time_s': round(elapsed, 1),
        'chunks_before': cs.get('count', 0),
        'chunks_after': ref.get('chunks_after', cs.get('count', 0)),
        'avg_before': cs.get('avg_chars', 0),
        'avg_after': ref.get('avg_chars', 0),
    }

    if result['status'] == 'completed' and not result.get('error'):
        status['processed'].append(entry)
        b, a = entry['chunks_before'], entry['chunks_after']
        growth = f'+{((a-b)/b*100):.0f}%' if b else '?'
        print(f'  ✅ {b}->{a} ({growth}) {elapsed:.0f}s')
    else:
        entry['error'] = result.get('error', 'unknown')
        status['failed'].append(entry)
        print(f'  ❌ {entry["error"]}')

    status['chunks_before'] += entry['chunks_before']
    status['chunks_after'] += entry['chunks_after']
    save_status(status)

    # Notify every 10 minutes
    if time.time() - last_notify >= NOTIFY_INTERVAL:
        elapsed_total = time.time() - status['started_at']
        done = len(status['processed']) + len(status['failed'])
        pct = f'{done}/{len(to_process)}'
        tb, ta = status['chunks_before'], status['chunks_after']
        growth = f'+{((ta-tb)/tb*100):.0f}%' if tb else '?'
        tg(f"Progress {pct} — {elapsed_total/60:.0f}m elapsed\n"
           f"✅ {len(status['processed'])} sukses | ❌ {len(status['failed'])} gagal\n"
           f"📊 {tb} -> {ta} chunks ({growth})\n"
           f"⏳ Sekarang: {status['current'][:50]}")
        last_notify = time.time()

# Final report
total_before = sum(p['chunks_before'] for p in status['processed'])
total_after = sum(p['chunks_after'] for p in status['processed'])
total_time = time.time() - status['started_at']
failed_count = len(status['failed'])
growth = f'+{((total_after-total_before)/total_before*100):.0f}%' if total_before else '?'

tg(f"Batch {status.get('batch',1)} SELESAI! {total_time/60:.0f}m\n"
   f"✅ {len(status['processed'])} sukses | ❌ {failed_count} gagal\n"
   f"📊 {total_before} -> {total_after} chunks ({growth})")

# Next batch: increment batch number for next run
status['batch'] = status.get('batch', 1) + 1
save_status(status)

print(f'\n🎉 Batch done: {total_before} -> {total_after} ({growth}) in {total_time/60:.0f}m')
