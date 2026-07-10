# 📄 Arcwright Forge — PDF Intelligence Pipeline

> **Extract, chunk, embed, and query any PDF — 100% free & open source.**
>
> Upload a PDF → get downloadable markdown + structured chunks + vector embeddings + RAG Q&A.
> No API keys. No paid services. Runs entirely on your machine.

---

## 📑 Table of Contents

- [Quick Start](#-quick-start)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [API Reference](#-api-reference)
- [Frontend Usage](#-frontend-usage)
- [Python Library Usage](#-python-library-usage)
- [Output Formats](#-output-formats)
- [OCR & Image-Based PDFs](#-ocr--image-based-pdfs)
- [FAQ](#-faq)
- [Development](#-development)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend dev)
- ~8GB free disk (for model downloads on first run)

### 1. Setup Backend

```bash
# Navigate to project
cd ~/Arcwright

# Activate virtual environment
source venv/bin/activate

# Install dependencies (first time only)
pip install -r forge/requirements.txt
pip install fastapi uvicorn python-multipart rank_bm25 aiofiles

# Start the API server
python forge/api/main.py
```

The API starts at **http://localhost:8765**.
API docs (Swagger UI) at **http://localhost:8765/docs**.

### 2. Setup Frontend (Development Mode)

```bash
# In a separate terminal
cd ~/Arcwright/forge/frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

The frontend starts at **http://localhost:5173**.

> **Note:** The Vite dev server proxies `/upload`, `/status`, `/download`, `/collections`, and `/chat` requests to the FastAPI backend automatically. No CORS issues.

### 3. Build Frontend for Production

```bash
cd ~/Arcwright/forge/frontend
npm run build
# Output in forge/frontend/dist/
```

### 4. Run a Quick Test

```bash
# Using curl (while API is running)
curl -X POST http://localhost:8765/upload \
  -F "file=@/path/to/sample.pdf" \
  -F "force_ocr=true"

# Check status (replace with your job_id)
curl http://localhost:8765/status/{job_id}

# When complete, download:
curl -O http://localhost:8765/download/{job_id}/markdown
curl -O http://localhost:8765/download/{job_id}/chunks
```

---

## 🛠️ Tech Stack

### Backend (Python)

| Component | Technology | License | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) | MIT | REST API server |
| **Server** | [Uvicorn](https://www.uvicorn.org/) | BSD | ASGI server |
| **PDF Extraction** | [marker-pdf](https://github.com/datalab-to/marker) | MIT/GPL/Apache | PDF → markdown with OCR |
| **Embedding Model** | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | MIT | Multilingual embeddings (1024-dim) |
| **Reranker** | [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | MIT | Cross-encoder reranking |
| **Vector Database** | [ChromaDB](https://www.trychroma.com/) | Apache 2.0 | Persistent vector storage |
| **Hybrid Search** | [rank_bm25](https://github.com/dorianbrown/rank_bm25) | Apache 2.0 | Keyword + vector hybrid retrieval |
| **Sentence Transformers** | [sentence-transformers](https://www.sbert.net/) | Apache 2.0 | Embedding inference |

### Frontend (JavaScript)

| Component | Technology | License | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | [React 19](https://react.dev/) | MIT | UI components |
| **Build Tool** | [Vite 8](https://vitejs.dev/) | MIT | Dev server + bundler |
| **Styling** | [Tailwind CSS 4](https://tailwindcss.com/) | MIT | Utility-first CSS (via CDN) |

### 💰 Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| All software | **$0** | MIT / Apache 2.0 licensed |
| Embedding model | **$0** | Runs locally on CPU |
| OCR | **$0** | marker-pdf with Surya OCR |
| Vector DB | **$0** | ChromaDB persistent, local |
| LLM for Q&A (optional) | **$0** | Use Ollama + local models |
| **Total** | **$0/month** | No API keys needed |

---

## 🏗️ Architecture

### High-Level Flow

```
                    ┌──────────────────────────────────┐
                    │         USER (Browser)           │
                    │   Drag & Drop PDF / View Results  │
                    └──────────────┬───────────────────┘
                                   │ HTTP / REST
                                   ▼
┌──────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                        │
│                                                          │
│  POST /upload ──→ Background Thread ──→ Pipeline         │
│       │                              │                   │
│       │                              ▼                   │
│       │                    ┌────────────────────┐        │
│       │                    │  1. marker-pdf     │        │
│       │                    │     OCR Extract    │        │
│       │                    │     → extracted.md │        │
│       │                    └────────┬───────────┘        │
│       │                             ▼                    │
│       │                    ┌────────────────────┐        │
│       │                    │  2. Semantic       │        │
│       │                    │     Chunking       │        │
│       │                    │     → chunks.json  │        │
│       │                    └────────┬───────────┘        │
│       │                             ▼                    │
│       │                    ┌────────────────────┐        │
│       │                    │  3. BGE-M3 Embed + │        │
│       │                    │     ChromaDB Store │        │
│       │                    │     → Collection   │        │
│       │                    └────────┬───────────┘        │
│       │                             ▼                    │
│       │                    ┌────────────────────┐        │
│       │                    │     COMPLETE       │        │
│       │                    │   Status: done     │        │
│       │                    └────────────────────┘        │
│       │                                                  │
│  GET /status/{id}  ←── Poll until "completed"           │
│                                                          │
│  GET /download/{id}/markdown  ←── Download markdown      │
│  GET /download/{id}/chunks    ←── Download chunks JSON   │
│                                                          │
│  POST /chat/{collection}  ←── RAG Q&A (bonus)           │
│                                                          │
│  GET /collections  ←── List all ChromaDB collections     │
└──────────────────────────────────────────────────────────┘
```

### Pipeline Detail

```
PDF File
    │
    ▼
┌─────────────────────┐
│ 1. EXTRACT          │  marker-pdf with force_ocr=True
│    (OCR if needed)  │  → Full markdown text
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 2. CHUNK            │  Heading-based semantic chunking:
│                     │  • H1 → section metadata
│                     │  • H2 → chapter boundary  
│                     │  • H3 → concept boundary
│                     │  • Min 100 chars, max 4000 chars
│                     │  → chunks.json array
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 3. EMBED & STORE    │  • BAAI/bge-m3 (1024-dim vectors)
│                     │  • ChromaDB PersistentClient
│                     │  • Batch size: 32 chunks
│                     │  • Metadata: title, section, source
│                     │  → ChromaDB collection
└──────────┬──────────┘
           ▼
    ┌──────────┐
    │  READY!  │  All outputs available for download + query
    └──────────┘
```

### ChromaDB Reuse Architecture

```
┌─────────────────────┐
│   Arcwright Forge   │  Creates collections per upload
│   forge/output/     │
│   chroma_db/        │
└──────────┬──────────┘
           │  Same filesystem — no network
           ▼
┌─────────────────────┐
│   Other Projects    │  pip install chromadb → connect directly
│   (LangChain, etc.) │  PersistentClient(path=".../chroma_db")
└─────────────────────┘
```

---

## 📁 Project Structure

```
Arcwright/
│
├── forge/                           ← 📦 ALL RAG CODE
│   │
│   ├── arcwright/                   ← Python package (modular pipeline)
│   │   ├── __init__.py              ← Package marker
│   │   ├── config.py                ← Configuration
│   │   ├── extract.py               ← PDF → markdown
│   │   ├── chunk.py                 ← Markdown → semantic chunks
│   │   ├── embed.py                 ← Chunks → embeddings → ChromaDB
│   │   └── pipeline.py              ← Orchestrator
│   │
│   ├── api/                         ← FastAPI backend
│   │   └── main.py                  ← API server (6 endpoints)
│   │
│   ├── frontend/                    ← React frontend
│   │   ├── index.html
│   │   ├── vite.config.js
│   │   ├── package.json
│   │   └── src/
│   │       ├── main.jsx
│   │       ├── index.css
│   │       ├── App.jsx
│   │       └── components/
│   │           ├── UploadZone.jsx
│   │           ├── JobStatus.jsx
│   │           ├── ChatPanel.jsx
│   │           └── CollectionList.jsx
│   │
│   ├── src/                         ← Original reference scripts
│   │   ├── 01-extract-pdf.py
│   │   ├── 02-chunk-markdown.py
│   │   └── 03-embed-and-test.py
│   │
│   ├── output/                      ← Pipeline artifacts (auto-generated)
│   │   ├── {collection}/            ← Per-PDF output
│   │   │   ├── extracted.md
│   │   │   └── chunks.json
│   │   └── chroma_db/               ← ChromaDB persistent storage
│   │
│   ├── data/                        ← Source PDFs & legacy extracts
│   ├── uploads/                     ← Temp uploads (auto-generated)
│   ├── requirements.txt
│   └── README.md                    ← This file
│
├── .bob/                            ← IBM Bob project markers
├── AGENTS.md                        ← AI agent instructions
├── README.md                        ← Root project overview
└── venv/                            ← Python virtual environment
```

---

## 📡 API Reference

All endpoints are documented interactively at **http://localhost:8765/docs** (Swagger UI).

### `POST /upload`

Upload a PDF and start the extraction pipeline.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | File (PDF) | ✅ | — | The PDF file to process |
| `force_ocr` | Boolean | ❌ | `true` | Enable OCR for scanned/image PDFs |
| `collection_name` | String | ❌ | auto | Custom ChromaDB collection name |

**Response:**
```json
{
  "job_id": "a1b2c3d4",
  "filename": "document.pdf",
  "collection": "document",
  "status": "processing",
  "check_status": "/status/a1b2c3d4"
}
```

### `GET /status/{job_id}`

Poll the status of a pipeline job.

```json
{
  "status": "completed",
  "collection": "document",
  "pdf_name": "document.pdf",
  "outputs": {
    "markdown": ".../extracted.md",
    "chunks": ".../chunks.json",
    "chroma_collection": "document"
  },
  "stats": {
    "extract": { "chars": 154320, "time_s": 45.2 },
    "chunk": { "count": 327, "avg_chars": 472 },
    "embed": { "collection": "document", "chunk_count": 327, "embed_time_s": 12.8 },
    "total_time_s": 60.1
  }
}
```

Status values: `processing`, `completed`, `error`.

### `GET /download/{job_id}/markdown`

Download the extracted markdown. → `text/markdown`

### `GET /download/{job_id}/chunks`

Download the chunks JSON. → `application/json`

### `GET /collections`

List all available ChromaDB collections.

```json
{
  "collections": [
    { "name": "document", "count": 327, "metadata": {} }
  ],
  "chroma_dir": ".../forge/output/chroma_db"
}
```

### `POST /chat/{collection_name}`

Query a processed PDF via RAG (bonus feature for testing).

```json
// Request
{ "query": "What is chapter 3 about?", "top_k": 5 }

// Response
{
  "query": "What is chapter 3 about?",
  "collection": "document",
  "sources": [
    { "id": "doc_abc", "title": "Chapter 3", "section": "Part I",
      "text": "The classical structure...", "distance": 0.2345 }
  ],
  "total_found": 5
}
```

---

## 🖥️ Frontend Usage

### Upload Page (`/`)

1. **Drop Zone** — Drag & drop a PDF file or click to browse
2. **Processing** — Progress indicator + status updates
3. **Job List** — Recent jobs listed on the left, click to view details
4. **Job Details** (right panel):
   - Pipeline statistics (chunks, time, extracted chars)
   - Download buttons for markdown and chunks JSON
   - ChromaDB collection info
   - RAG Q&A panel for testing

### Collections Page (`/collections`)

- Lists all ChromaDB collections with chunk counts
- Shows Python code snippet for accessing each collection
- Collections persist between API restarts

---

## 🐍 Python Library Usage

The `arcwright/` package can be imported from any Python script.

### Extract PDF

```python
from forge.arcwright import extract

markdown = extract.extract_pdf("path/to/book.pdf", force_ocr=True)
print(f"Extracted {len(markdown)} characters")
```

### Chunk Markdown

```python
from forge.arcwright import chunk

chunks = chunk.chunk_markdown(markdown, source_name="My Book")
print(f"Generated {len(chunks)} chunks")
```

### Embed & Store

```python
from forge.arcwright import embed

stats = embed.embed_and_store(chunks, collection_name="my_book")
print(f"Stored {stats['chunk_count']} chunks")
```

### Full Pipeline

```python
from forge.arcwright import pipeline

results = pipeline.run_pipeline(
    pdf_path="path/to/book.pdf",
    collection_name="my_book",
    force_ocr=True,
)
print(f"Status: {results['status']}")
print(f"Chunks: {results['stats']['chunk']['count']}")
```

### Access ChromaDB from External Projects

```python
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="/path/to/Arcwright/forge/output/chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

collection = client.get_collection("my_book")
# Now you can query, add, delete, etc.
```

---

## 📦 Output Formats

### `extracted.md`

Full markdown from PDF with OCR. Headings, paragraphs, lists, tables preserved.

### `chunks.json`

```json
[
  {
    "id": "my_book_a1b2c3d4",
    "title": "The Hero's Journey",
    "section": "Part II: Story Structure",
    "source": "my_book",
    "text": "The hero's journey typically begins with...",
    "char_count": 487
  }
]
```

### ChromeDB Collection

Persistent vector database at `forge/output/chroma_db/`. Each PDF gets its own collection with 1024-dim BGE-M3 embeddings and rich metadata.

---

## 🔍 OCR & Image-Based PDFs

| PDF Type | `force_ocr=true` (default) | `force_ocr=false` |
|----------|---------------------------|-------------------|
| **Digital PDF** (selectable text) | OCR runs (slower but accurate) | Text extraction only (faster) |
| **Scanned PDF** (image-only) | ✅ Extracts text | ❌ Empty output |
| **Mixed** (text + images) | OCR runs on everything | Text extracted, images skipped |

**Recommendation:** Keep `force_ocr=true` (default).

> **First run:** marker-pdf downloads OCR models (~2GB). Subsequent runs use cache.

---

## ❓ FAQ

**Q: Does this need internet?**  
Only for first run (model downloads ~4GB). After that, fully offline.

**Q: Can other projects use the ChromaDB collections?**  
Yes! Any Python project with `chromadb` installed can connect directly to `forge/output/chroma_db/`.

**Q: What languages does the embedding support?**  
100+ languages via BAAI/bge-m3 (top-ranked on MTEB leaderboard).

**Q: How long does processing take?**  
| File Size | Digital PDF | Scanned (OCR) |
|-----------|-------------|---------------|
| 1 MB | ~10s | ~30s |
| 10 MB | ~30s | ~2min |
| 50 MB | ~2min | ~8min |

**Q: Can I process multiple PDFs?**  
Yes, each upload creates its own collection. They queue up and process one at a time.

---

## 🛠️ Development

### Testing

```bash
# Test Python imports
source venv/bin/activate
cd ~/Arcwright
python -c "from forge.arcwright import extract, chunk, embed, pipeline; print('✅ OK')"

# Test API
curl http://localhost:8765/
curl http://localhost:8765/collections
```

### Modifying the Pipeline

| File | What to change |
|------|---------------|
| `forge/arcwright/config.py` | Model names, chunk sizes, paths |
| `forge/arcwright/extract.py` | OCR settings, PDF converter options |
| `forge/arcwright/chunk.py` | Chunking strategy, sizes, metadata |
| `forge/arcwright/embed.py` | Batch size, embedding model, ChromaDB |
| `forge/arcwright/pipeline.py` | Pipeline flow, error handling |

### Adding New Features

1. **New output format** → Add step in `pipeline.py` + endpoint in `api/main.py`
2. **New embedding model** → Change `EMBEDDING_MODEL` in `config.py`
3. **New frontend page** → Add route in `App.jsx` + new component

---

## 📄 License

All components are open source: MIT / Apache 2.0.

---

*Built with ❤️ — part of the Arcwright project*
