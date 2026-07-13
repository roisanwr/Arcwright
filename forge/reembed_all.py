"""Re-embed all existing chunks from output dirs back into ChromaDB."""
import sys, json, time, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arcwright import config
from arcwright.embed import get_embedding_model, get_chroma_client, embed_and_store

OUTPUT_DIR = config.OUTPUT_DIR
CHROMA_DIR = config.CHROMA_DIR
COLLECTION = "storytelling_books"

# Find all output dirs with chunks.json
book_dirs = sorted([d for d in OUTPUT_DIR.iterdir() 
                    if d.is_dir() and d.name not in ("chroma_db", "test_verify")])

all_chunks = []
slugs = []
for d in book_dirs:
    chunks_file = d / "chunks.json"
    if chunks_file.exists():
        try:
            with open(chunks_file) as f:
                chunks = json.load(f)
            # Check it's a list of chunks (not a dict/collection dump)
            if isinstance(chunks, list) and len(chunks) > 0 and "text" in chunks[0]:
                all_chunks.extend(chunks)
                slugs.append(d.name)
                print(f"  📖 {d.name}: {len(chunks)} chunks")
            elif isinstance(chunks, list) and len(chunks) > 0:
                print(f"  ⚠️  {d.name}: {len(chunks)} items but no 'text' key — skipping")
            else:
                print(f"  ⚠️  {d.name}: empty chunks.json")
        except Exception as e:
            print(f"  ❌ {d.name}: {e}")
    # Also check test_collection_sg
    test_dir = d / ".." / "test_collection_sg"
    
print(f"\n📊 Total: {len(all_chunks)} chunks from {len(slugs)} books")

# Dedup by ID
seen_ids = set()
unique_chunks = []
for c in all_chunks:
    if c["id"] not in seen_ids:
        seen_ids.add(c["id"])
        unique_chunks.append(c)

print(f"📊 Unique chunks (by ID): {len(unique_chunks)}")

# Load model once
print(f"\n🧠 Loading embedding model...")
embed_model = get_embedding_model()

# Embed in batches of 500 chunks at a time
BATCH_SIZE = 200
total_embedded = 0
for i in range(0, len(unique_chunks), BATCH_SIZE):
    batch = unique_chunks[i:i+BATCH_SIZE]
    print(f"\n📦 Batch {i//BATCH_SIZE + 1}/{(len(unique_chunks)-1)//BATCH_SIZE + 1}: {len(batch)} chunks")
    stats = embed_and_store(batch, COLLECTION, embed_model=embed_model, replace=(i==0))
    total_embedded += stats.get("new_count", len(batch))
    print(f"   Collection now has {stats.get('chunk_count', '?')} total")

print(f"\n✅ DONE! {total_embedded} chunks embedded into '{COLLECTION}'")
