# Storytelling AI — RAG Knowledge Base

Multi-agent storytelling system powered by LangGraph + RAG.
This repo contains the RAG pipeline for processing storytelling books.

## 📁 Struktur Proyek

```
storytelling-ai/
├── data/
│   ├── books/                  ← PDF buku asli
│   │   └── Robert McKee - Story (pdf).pdf
│   ├── extracted/              ← Hasil OCR (markdown)
│   │   └── Robert McKee - Story (pdf).md
│   └── chunks.json             ← 327 chunks siap RAG
├── src/
│   ├── 01-extract-pdf.py       ← PDF → Markdown (pake marker-pdf)
│   ├── 02-chunk-markdown.py    ← Markdown → Chunks per konsep
│   └── 03-embed-and-test.py    ← Chunks → Embedding → ChromaDB + Test
├── chroma_db/                  ← Vector database
├── venv/                       ← Virtual environment
├── requirements.txt
└── .gitignore
```

## 🚀 Cara Pakai

```bash
# 1. Aktifkan venv
source venv/bin/activate

# 2. Ekstrak PDF baru
python src/01-extract-pdf.py

# 3. Chunk hasil ekstraksi
python src/02-chunk-markdown.py

# 4. Embed + simpan ke ChromaDB
python src/03-embed-and-test.py
```

## 📊 Status RAG

| Buku | Status | Chunks |
|------|--------|--------|
| Robert McKee — Story | ✅ Done | 327 |

## 🧠 Chunking Strategy

Tiap chunk dipotong per konsep (`###` heading), bukan per halaman.
Ini bikin retrievel lebih presisi — pas query "inciting incident", dapet langsung bab spesifik.
