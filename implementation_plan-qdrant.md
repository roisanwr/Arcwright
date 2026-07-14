# Migration Plan: ChromaDB → Docker Qdrant (Linux PC)

## Latar Belakang

ChromaDB menyimpan HNSW index dalam format binary yang **terikat pada arsitektur OS** tempat index tersebut dibuat. Karena proses embedding kamu dijalankan di Linux, index tersebut tidak bisa dibaca langsung di Windows.

**Solusi: Qdrant + Docker.**

Qdrant yang dijalankan dalam Docker container selalu berjalan di atas Linux, tidak peduli di OS host mana Docker-nya berjalan (Linux, Windows, atau Mac). Ini berarti data Qdrant yang dibuat di PC Linux kamu bisa di-zip, dipindahkan ke PC Windows atau PC Server mana saja, dan **100% langsung terbaca tanpa corrupt**.

---

## Arsitektur Baru (Setelah Migrasi)

```
Arcwright/
├── forge/                   ← Pipeline ekstraksi PDF (Python biasa, no Docker)
│   └── arcwright/
│       └── embed.py         ← ⚠️  DIGANTI: kirim ke Qdrant HTTP, bukan Chroma file
├── agents/
│   └── rag_librarian.py     ← ⚠️  DIGANTI: connect ke Qdrant HTTP
├── config/
│   └── settings.py          ← ⚠️  DIGANTI: CHROMA_DIR → QDRANT_URL
├── requirements.txt         ← ⚠️  DIGANTI: chromadb → qdrant-client
├── docker-compose.yml       ← 🆕  BARU: definisi Qdrant server
└── qdrant_storage/          ← 🆕  BARU: folder data Qdrant (di-gitignore)
```

**Konsep aliran data:**
```
Script Python ──(HTTP)──► Qdrant Docker Container
                          └── /qdrant/storage (volume di host = qdrant_storage/)
```

---

## File-File yang Perlu Diubah

### LAYER 0 — Docker Setup (File Baru)

#### [NEW] `docker-compose.yml` (di root project)
```yaml
version: "3.9"
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: arcwright_qdrant
    ports:
      - "6333:6333"   # REST API (yang dipakai Python)
      - "6334:6334"   # gRPC (opsional, untuk performa tinggi)
    volumes:
      - ./qdrant_storage:/qdrant/storage  # data tersimpan di folder lokal
    restart: unless-stopped
    environment:
      - QDRANT__LOG_LEVEL=INFO
```

> **Penjelasan volume:** `./qdrant_storage` adalah folder di PC kamu (di-gitignore). Semua data vektor disimpan di sini. Kalau mau pindah ke PC Server, folder ini yang di-zip/copy.

#### [MODIFY] `.gitignore`
Tambahkan baris:
```
qdrant_storage/
```

---

### LAYER 1 — Dependencies

#### [MODIFY] `requirements.txt` (root — untuk agent pipeline)
```diff
- langchain-chroma>=0.2.0
- chromadb>=0.6.0
+ langchain-qdrant>=0.2.0
+ qdrant-client>=1.9.0
```

#### [MODIFY] `forge/requirements.txt` (untuk forge pipeline)
```diff
- chromadb>=0.6.0
+ qdrant-client>=1.9.0
```

---

### LAYER 2 — Konfigurasi

#### [MODIFY] `config/settings.py`

```diff
- CHROMA_DIR   = PROJECT_ROOT / "forge" / "output" / "chroma_db"
+ QDRANT_URL        = os.getenv("QDRANT_URL", "http://localhost:6333")
+ QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "storytelling_books")
```

Tambahkan juga di bagian `.env`:
```env
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=storytelling_books
```

#### [MODIFY] `forge/arcwright/config.py`

```diff
- CHROMA_DIR = OUTPUT_DIR / "chroma_db"
- CHROMA_DIR.mkdir(parents=True, exist_ok=True)
+ import os
+ QDRANT_URL        = os.getenv("QDRANT_URL", "http://localhost:6333")
+ QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "storytelling_books")
- CHROMA_COLLECTION_PREFIX = "arcwright_"
+ COLLECTION_NAME = QDRANT_COLLECTION
```

---

### LAYER 3 — Forge Embedding Engine (Inti)

#### [MODIFY] `forge/arcwright/embed.py`

Ini file paling krusial. Seluruh logika ChromaDB diganti dengan Qdrant client.

```python
"""
Embedding & vector storage module.
Uses BAAI/bge-m3 (free, open-source, multilingual, 1024-dim).
Stores in Qdrant (Docker, OS-agnostic, production-grade).
"""
import uuid
import time
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, PayloadSchemaType
)

from . import config


def get_embedding_model(model_name: str = None) -> SentenceTransformer:
    """Load the sentence-transformers embedding model."""
    if model_name is None:
        model_name = config.EMBEDDING_MODEL
    print(f"  Loading embedding model: {model_name}...")
    return SentenceTransformer(model_name)


def get_qdrant_client(url: str = None) -> QdrantClient:
    """Connect ke Qdrant server (Docker)."""
    if url is None:
        url = config.QDRANT_URL
    return QdrantClient(url=url)


def ensure_collection(client: QdrantClient, collection_name: str, replace: bool = False):
    """Buat collection jika belum ada, atau hapus dan buat ulang jika replace=True."""
    existing = [c.name for c in client.get_collections().collections]

    if replace and collection_name in existing:
        client.delete_collection(collection_name)
        print(f"  Removed existing collection: {collection_name}")
        existing = []

    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
        # Payload index untuk filter cepat berdasarkan metadata
        client.create_payload_index(collection_name, "source", PayloadSchemaType.KEYWORD)
        client.create_payload_index(collection_name, "title", PayloadSchemaType.KEYWORD)
        print(f"  Created new collection: {collection_name}")


def embed_and_store(chunks: list, collection_name: str,
                    embed_model: SentenceTransformer = None,
                    qdrant_url: str = None,
                    replace: bool = False) -> dict:
    """
    Embed chunks dan simpan ke Qdrant collection.

    Args:
        chunks: List of chunk dicts dari chunk_markdown()
        collection_name: Nama collection Qdrant
        embed_model: Pre-loaded embedding model (atau None untuk load otomatis)
        qdrant_url: URL Qdrant server (default: dari config)
        replace: Jika True, hapus dan buat ulang collection

    Returns:
        Dict dengan statistik hasil embedding
    """
    if embed_model is None:
        embed_model = get_embedding_model()

    client = get_qdrant_client(qdrant_url)
    ensure_collection(client, collection_name, replace=replace)

    # Cek existing IDs untuk dedup
    existing_count = client.count(collection_name).count
    
    # Filter chunks yang belum ada
    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [
        {
            "title":      c["title"][:200],
            "section":    c["section"][:200],
            "source":     c["source"][:100],
            "char_count": c["char_count"],
        }
        for c in chunks
    ]

    # Embedding dalam batch
    batch_size = 32
    start = time.time()
    all_points = []

    for i in range(0, len(chunks), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_ids   = ids[i:i+batch_size]
        batch_meta  = metadatas[i:i+batch_size]

        embeddings = embed_model.encode(batch_texts, show_progress_bar=False)

        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, bid)),  # string ID → UUID
                vector=emb.tolist(),
                payload={**meta, "text": text},
            )
            for bid, text, emb, meta in zip(batch_ids, batch_texts, embeddings, batch_meta)
        ]
        all_points.extend(points)

    # Upload ke Qdrant dalam batch besar
    UPLOAD_BATCH = 200
    for i in range(0, len(all_points), UPLOAD_BATCH):
        client.upsert(
            collection_name=collection_name,
            points=all_points[i:i+UPLOAD_BATCH],
        )

    elapsed = time.time() - start
    new_count = client.count(collection_name).count

    print(f"  ✅ {len(chunks)} chunks embedded & stored in {elapsed:.1f}s")
    print(f"     Collection: {collection_name} ({new_count} total)")

    return {
        "collection": collection_name,
        "chunk_count": new_count,
        "existing_count": existing_count,
        "new_count": len(chunks),
        "embed_time_s": round(elapsed, 1),
        "qdrant_url": qdrant_url or config.QDRANT_URL,
    }


def list_collections(qdrant_url: str = None) -> list:
    """List semua Qdrant collections yang tersedia."""
    client = get_qdrant_client(qdrant_url)
    collections = client.get_collections().collections
    return [
        {
            "name": c.name,
            "count": client.count(c.name).count,
        }
        for c in collections
    ]
```

---

### LAYER 4 — Agent RAG Librarian

#### [MODIFY] `agents/rag_librarian.py`

```diff
- from langchain_chroma import Chroma
+ from langchain_qdrant import QdrantVectorStore
+ from qdrant_client import QdrantClient

def _build_rag_tool():
-     vector_store = Chroma(
-         persist_directory=str(settings.CHROMA_DIR),
-         embedding_function=embeddings,
-         collection_name=settings.CHROMA_COLLECTION,
-     )
+     qdrant_client = QdrantClient(url=settings.QDRANT_URL)
+     vector_store = QdrantVectorStore(
+         client=qdrant_client,
+         collection_name=settings.QDRANT_COLLECTION,
+         embedding=embeddings,
+     )
```

---

### LAYER 5 — Forge Re-embed Script

#### [MODIFY] `forge/reembed_all.py`

Ubah variabel referensi dari `CHROMA_DIR` ke `QDRANT_URL`:
```diff
- CHROMA_DIR = config.CHROMA_DIR
- COLLECTION = "storytelling_books"
+ QDRANT_URL  = config.QDRANT_URL
+ COLLECTION  = config.QDRANT_COLLECTION

# Pada pemanggilan embed_and_store:
- stats = embed_and_store(batch, COLLECTION, embed_model=embed_model, replace=(i==0))
+ stats = embed_and_store(batch, COLLECTION, embed_model=embed_model,
+                         qdrant_url=QDRANT_URL, replace=(i==0))
```

---

## Panduan Eksekusi Step-by-Step (di PC Linux)

### Step 1 — Persiapan Docker

```bash
# Pastikan Docker terinstall
docker --version

# Jalankan Qdrant server
docker compose up -d

# Verifikasi Qdrant berjalan
curl http://localhost:6333/healthz
# Expected: {"title":"qdrant - vector search engine","version":"..."}
```

### Step 2 — Install Dependencies Baru

```bash
# Di root project
pip install qdrant-client langchain-qdrant
pip uninstall chromadb langchain-chroma -y

# Di forge/
pip install qdrant-client
pip uninstall chromadb -y
```

### Step 3 — Set Environment Variables

Tambahkan ke file `.env`:
```env
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=storytelling_books
```

### Step 4 — Terapkan Perubahan Kode

Terapkan semua perubahan file yang dijelaskan di atas (bisa minta saya kerjakan otomatis).

### Step 5 — Jalankan Re-embedding

```bash
# Ini sekarang akan mengirim data ke Qdrant Docker, bukan ke file lokal
PYTHONIOENCODING=utf-8 python forge/reembed_all.py
```

Proses ini akan memanfaatkan GPU jika tersedia (jauh lebih cepat dari Windows CPU kamu).

### Step 6 — Verifikasi

```bash
python -c "
from qdrant_client import QdrantClient
c = QdrantClient('http://localhost:6333')
col = c.get_collection('storytelling_books')
print(f'Total: {col.vectors_count} chunks')
"
# Expected: Total: ~9270 chunks
```

### Step 7 — Pindah ke PC Server (atau Windows)

```bash
# Matikan Qdrant dulu
docker compose down

# Zip folder data
tar -czf qdrant_backup_$(date +%Y%m%d).tar.gz qdrant_storage/

# Di PC tujuan:
# 1. Copy file .tar.gz
# 2. Extract: tar -xzf qdrant_backup_YYYYMMDD.tar.gz
# 3. Jalankan: docker compose up -d
# 4. Langsung siap! Tidak ada embedding ulang.
```

---

## Summary Perubahan

| File | Status | Perubahan Utama |
|---|---|---|
| `docker-compose.yml` | 🆕 BARU | Definisi Qdrant server + volume |
| `.gitignore` | ⚠️ MODIFIKASI | Tambah `qdrant_storage/` |
| `requirements.txt` | ⚠️ MODIFIKASI | Ganti chromadb → qdrant-client |
| `forge/requirements.txt` | ⚠️ MODIFIKASI | Ganti chromadb → qdrant-client |
| `config/settings.py` | ⚠️ MODIFIKASI | `CHROMA_DIR` → `QDRANT_URL` + `QDRANT_COLLECTION` |
| `forge/arcwright/config.py` | ⚠️ MODIFIKASI | `CHROMA_DIR` → `QDRANT_URL` + `QDRANT_COLLECTION` |
| `forge/arcwright/embed.py` | ⚠️ MODIFIKASI | Seluruh logika ChromaDB → Qdrant client |
| `agents/rag_librarian.py` | ⚠️ MODIFIKASI | `langchain_chroma.Chroma` → `langchain_qdrant.QdrantVectorStore` |
| `forge/reembed_all.py` | ⚠️ MODIFIKASI | Argumen `chroma_dir` → `qdrant_url` |
| `.env` | ⚠️ MODIFIKASI | Tambah `QDRANT_URL` dan `QDRANT_COLLECTION` |
