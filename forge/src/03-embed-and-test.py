#!/usr/bin/env python3
"""
Step 3: Embed chunks & store in ChromaDB
Step 4: Query test
"""
import json
import os
import time
import sys

CHUNKS_PATH = os.path.expanduser("~/rag-storytelling-output/chunks.json")
CHROMA_DIR = os.path.expanduser("~/rag-storytelling-output/chroma_db")

# Load chunks
with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loading {len(chunks)} chunks into ChromaDB...")

# --- Init embedding model ---
print("Loading embedding model...", end=" ", flush=True)
from sentence_transformers import SentenceTransformer
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
print("✅")

# --- Init ChromaDB ---
import chromadb
from chromadb.config import Settings

# Delete existing DB if any
if os.path.exists(CHROMA_DIR):
    import shutil
    shutil.rmtree(CHROMA_DIR)

client = chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False))

# Create collection
collection = client.create_collection(
    name="storytelling_books",
    metadata={"description": "Books about storytelling craft - RAG for Storytelling AI"}
)

# --- Prepare data for ChromaDB ---
ids = [c["id"] for c in chunks]
texts = [c["text"] for c in chunks]

metadatas = []
for c in chunks:
    metadatas.append({
        "title": c["title"],
        "section": c["section"],
        "book": c["book"],
        "author": c["author"],
        "char_count": str(c["char_count"]),
    })

# --- Embed & Store ---
batch_size = 50
print(f"Embedding and storing {len(chunks)} chunks in batches of {batch_size}...")

start = time.time()
for i in range(0, len(chunks), batch_size):
    batch_end = min(i + batch_size, len(chunks))
    batch_texts = texts[i:batch_end]
    batch_ids = ids[i:batch_end]
    batch_metadatas = metadatas[i:batch_end]
    
    # Embed
    embeddings = embed_model.encode(batch_texts, show_progress_bar=False)
    
    # Store
    collection.add(
        ids=batch_ids,
        embeddings=embeddings.tolist(),
        documents=batch_texts,
        metadatas=batch_metadatas,
    )
    
    print(f"  Batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}: {len(batch_texts)} chunks embedded & stored", flush=True)

elapsed = time.time() - start
print(f"\n✅ Done! {len(chunks)} chunks stored in ChromaDB ({elapsed:.1f}s)")
print(f"   DB location: {CHROMA_DIR}")

# --- Test Query ---
print("\n" + "="*50)
print("🧪 TEST QUERY")
print("="*50)

def query_rag(query_text, n_results=3):
    query_embedding = embed_model.encode([query_text])
    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=n_results,
    )
    return results

test_queries = [
    "What makes a good story opening hook?",
    "How does the inciting incident work?",
    "What is the difference between plot and structure?",
    "character vs character conflict",
]

for q in test_queries:
    print(f"\n❓ Query: {q}")
    print("-"*50)
    results = query_rag(q)
    
    for j, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    )):
        print(f"\n  #{j+1} [{meta['section']} → {meta['title']}] (dist: {dist:.3f})")
        preview = doc[:200].replace('\n', ' ')
        print(f"     {preview}...")
    print()

print("="*50)
print("✅ RAG pipeline siap digunakan!")
