#!/usr/bin/env python3
"""Force-refine ALL remaining books — even those without old chunks."""
import os, sys, time, json, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ['LLM_API_URL'] = 'https://opencode.ai/zen/v1'
os.environ['LLM_API_KEY'] = 'public'
os.environ['LLM_MODEL'] = 'deepseek-v4-flash-free'

from arcwright.pipeline import run_pipeline
from arcwright import config
from arcwright.extract import SUPPORTED_FORMATS

STATUS_FILE = config.OUTPUT_DIR / 'batch_refine_status.json'
last_notify = time.time()
NOTIFY_INTERVAL = 600

def tg(msg):
    os.system(f'hermes send -t telegram "🔬 Arcwright: {msg}" > /dev/null 2>&1')

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

# Get all unique books
all_books = sorted(config.BOOKS_DIR.glob('*'))
supported = [b for b in all_books if b.suffix.lower() in SUPPORTED_FORMATS]
groups = {}
for b in supported:
    groups.setdefault(normalize(b.name), []).append(b)
FORMAT_PREF = ['.pdf', '.epub', '.mobi', '.azw3', '.docx', '.txt', '.html']
unique_books = []
for norm, versions in groups.items():
    versions.sort(key=lambda v: FORMAT_PREF.index(v.suffix.lower()) if v.suffix.lower() in FORMAT_PREF else 99)
    unique_books.append(versions[0])

# Get all refined slugs (from chunks_refined.json on disk)
refined_slugs = set()
for d in config.OUTPUT_DIR.iterdir():
    if d.is_dir() and d.name.startswith('refined_'):
        rf = d / 'chunks_refined.json'
        if rf.exists():
            with open(rf) as f:
                chunks = json.load(f)
            if isinstance(chunks, list) and len(chunks) > 0:
                refined_slugs.add(d.name.replace('refined_', ''))

# Find books NOT yet refined
to_do = []
for b in unique_books:
    slug = make_slug(b)
    found = False
    for rs in refined_slugs:
        if slug[:20] in rs or rs[:20] in slug:
            found = True
            break
    if not found:
        to_do.append(b)

# Also try loading old status to count already-processed
status = {}
if STATUS_FILE.exists():
    with open(STATUS_FILE) as f:
        status = json.load(f)

already_processed = len(status.get('processed', []))
already_failed = len(status.get('failed', []))

print(f'Total unique books in library: {len(unique_books)}')
print(f'Already refined (verified on disk): {len(refined_slugs)}')
print(f'Already in status file (processed+failed): {already_processed+already_failed}')
print(f'Books NOT yet refined: {len(to_do)}')
print()
for b in to_do:
    ext = b.suffix.upper().strip('.')
    size = b.stat().st_size / (1024*1024)
    print(f'  📖 {b.name} ({ext}, {size:.1f}MB)')

if not to_do:
    print(f'\n🎉 SEMUA BUKU SUDAH DI-REFINE!')
    total = 0
    for d in config.OUTPUT_DIR.iterdir():
        if d.is_dir() and d.name.startswith('refined_'):
            rf = d / 'chunks_refined.json'
            if rf.exists():
                with open(rf) as f:
                    total += len(json.load(f))
    print(f'Total refined chunks: {total}')
    
    # Count old chunks too for comparison
    old_total = 0
    for d in config.OUTPUT_DIR.iterdir():
        if d.is_dir() and d.name != 'chroma_db' and not d.name.startswith(('rechunk_','refined_','compare_','6layer_','full6layer_','test_','_')):
            cf = d / 'chunks.json'
            if cf.exists():
                with open(cf) as f:
                    ch = json.load(f)
                if isinstance(ch, list) and len(ch) > 0 and 'text' in ch[0]:
                    old_total += len(ch)
    print(f'Old chunks (before refine): ~{old_total}')
    if old_total:
        print(f'Growth: +{((total-old_total)/old_total*100):.0f}%')
    sys.exit(0)

tg(f"Refine {len(to_do)} buku sisa — GPU batch_size=32")

for idx, book_path in enumerate(to_do):
    col_name = f'refined_{make_slug(book_path)}'[:50]
    print(f'\n[{idx+1}/{len(to_do)}] {book_path.name}')
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

    # Save to status
    status.setdefault('processed', []).append(entry)

    if result['status'] == 'completed' and not result.get('error'):
        growth = f'+{((chunks_after-chunks_before)/chunks_before*100):.0f}%' if chunks_before else '?'
        print(f'  ✅ {chunks_before}->{chunks_after} ({growth}) {elapsed:.0f}s')
    else:
        entry['error'] = result.get('error', 'unknown')
        status.setdefault('failed', []).append(entry)
        print(f'  ❌ {entry["error"]}')

    # Continuously save status
    status['chunks_before'] = sum(p.get('chunks_before', 0) for p in status.get('processed', []))
    status['chunks_after'] = sum(p.get('chunks_after', 0) for p in status.get('processed', []))
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2)

    # Notify every 10 min
    if time.time() - last_notify >= NOTIFY_INTERVAL:
        done = len(status.get('processed', [])) + len(status.get('failed', []))
        tb = status['chunks_before']
        ta = status['chunks_after']
        growth = f'+{((ta-tb)/tb*100):.0f}%' if tb else '?'
        tg(f"Progress {done}/{len(to_do)} — {elapsed/60:.0f}m elapsed\n"
           f"✅ {len(status.get('processed', []))} sukses\n"
           f"📊 {tb} -> {ta} chunks ({growth})\n"
           f"⏳ {book_path.name[:50]}")
        last_notify = time.time()

# Final report
total_before = sum(p.get('chunks_before', 0) for p in status.get('processed', []))
total_after = sum(p.get('chunks_after', 0) for p in status.get('processed', []))
total_time = time.time() - status.get('started_at', time.time())
growth = f'+{((total_after-total_before)/total_before*100):.0f}%' if total_before else '?'

print(f'\n{"="*60}')
print(f'🎉 SEMUA SELESAI!')
print(f'{"="*60}')
print(f'Total books refined: {len(refined_slugs) + len(to_do)}')
print(f'Chunks: {total_before} -> {total_after} ({growth})')
print(f'Time: {total_time:.0f}s ({total_time/60:.1f} min)')

# Full book count
all_refined = set(refined_slugs)
for b in to_do:
    all_refined.add(make_slug(b))
print(f'\nTotal refined output dirs: {len(all_refined)}')

tg(f"SELESAI! {len(all_refined)} buku di-refine\n"
   f"📊 {total_before} -> {total_after} chunks ({growth})\n"
   f"⏱ {total_time/60:.0f} menit total")
