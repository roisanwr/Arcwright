# 📄 Arcwright — PDF Intelligence Pipeline

> **Extract, chunk, embed, and query any PDF — 100% free & open source.**
>
> Upload a PDF → get downloadable markdown + structured chunks + vector embeddings + RAG Q&A.
> No API keys. No paid services. Runs entirely on your machine.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Frontend Usage](#-frontend-usage)
- [Python Library Usage](#-python-library-usage)
- [Output Formats](#-output-formats)
- [OCR & Image-Based PDFs](#-ocr--image-based-pdfs)
- [FAQ](#-faq)
- [Development](#-development)
- [License](#-license)

---

## 🎯 Overview

Arwright transforms any PDF (digital or scanned) into reusable data:

| Input | → | Output | Purpose |
|-------|---|--------|---------|
| 📄 **Any PDF** | → | **extracted.md** | Full text with OCR — readable, editable |
| | → | **chunks.json** | Structured, chunked data for other systems |
| | → | **ChromaDB collection** | Vector embeddings — queryable from any Python project |
| | → | **RAG Q&A** (bonus) | Test retrieval quality via chat interface |

Built for:
- 📚 Digitizing books and documents
- 🔬 Building RAG knowledge bases
- 🤖 Feeding extracted data into AI agents and pipelines
- 🧪 Experimenting with chunking, embedding, and retrieval strategies

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
| **Icons** | SVG inline | — | Custom icons |

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
│   Arcwright API     │  Creates collections per upload
│   output/chroma_db/ │
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
├── arcwright/                         # 📦 Python package (modular pipeline)
│   ├── __init__.py                    # Package marker
│   ├── config.py                      # Configuration (paths, models, defaults)
│   ├── extract.py                     # PDF → markdown (marker-pdf + OCR)
│   ├── chunk.py                       # Markdown → semantic chunks
│   ├── embed.py                       # Chunks → embeddings → ChromaDB
│   └── pipeline.py                    # Orchestrator: extract → chunk → embed
│
├── api/                               # 🌐 FastAPI backend
│   └── main.py                        # API server (6 endpoints)
│
├── frontend/                          # ⚛️ React frontend
│   ├── index.html                     # Entry HTML (Tailwind CDN)
│   ├── vite.config.js                 # Vite config + API proxy
│   ├── package.json                   # Dependencies
│   ├── public/                        # Static assets
│   │   ├── favicon.svg
│   │   └── icons.svg
│   └── src/
│       ├── main.jsx                   # React entry point
│       ├── index.css                  # Global styles
│       ├── App.jsx                    # Main app component
│       └── components/
│           ├── UploadZone.jsx          # Drag & drop PDF upload
│           ├── JobStatus.jsx           # Processing status card
│           ├── ChatPanel.jsx           # RAG Q&A interface
│           └── CollectionList.jsx      # ChromaDB collections browser
│
├── src/                               # 📜 Original scripts (reference)
│   ├── 01-extract-pdf.py
│   ├── 02-chunk-markdown.py
│   └── 03-embed-and-test.py
│
├── data/                              # 📂 Data directory
│   ├── books/                         # Raw PDF files (manual placement)
│   └── extracted/                     # Legacy extraction output
│
├── output/                            # 📦 Pipeline output (auto-created)
│   ├── {collection_name}/             # Per-PDF output folder
│   │   ├── extracted.md               # Full extracted text
│   │   └── chunks.json                # Semantic chunks
│   └── chroma_db/                     # ChromaDB persistent storage
│       ├── chroma.sqlite3
│       └── ... (vector index files)
│
├── uploads/                           # 📤 Temporary upload storage (auto-created)
│
├── venv/                              # 🐍 Python virtual environment
│
├── requirements.txt                   # Python dependencies
├── README.md                          # This file
├── AGENTS.md                          # AI agent instructions (IBM Bob format)
├── .gitignore                         # Git ignore rules
└── .bob/                              # 🤖 IBM Bob project markers
    ├── bob.yaml
    ├── settings.json
    ├── modes/
    │   ├── code.md
    │   └── plan.md
    └── skills/
        └── arcwright-pipeline.md
```

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
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart rank_bm25 aiofiles

# Start the API server
python api/main.py
```

The API starts at **http://localhost:8765**.
API docs (Swagger UI) at **http://localhost:8765/docs**.

### 2. Setup Frontend (Development Mode)

```bash
# In a separate terminal
cd ~/Arcwright/frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

The frontend starts at **http://localhost:5173**.

> **Note:** The Vite dev server proxies `/upload`, `/status`, `/download`, `/collections`, and `/chat` requests to the FastAPI backend automatically. No CORS issues.

### 3. Build Frontend for Production

```bash
cd ~/Arcwright/frontend
npm run build
# Output in frontend/dist/
```

To serve the production build via FastAPI, add static file mounting to `api/main.py`:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="frontend")
```

### 4. Run a Quick Test

```bash
# Using curl (while API is running)
curl -X POST http://localhost:8765/upload \
  -F "file=@/path/to/sample.pdf" \
  -F "force_ocr=true"

# Check status
# Returns a job_id — poll with:
curl http://localhost:8765/status/{job_id}

# When complete, download:
curl -O http://localhost:8765/download/{job_id}/markdown
curl -O http://localhost:8765/download/{job_id}/chunks
```

---

## 📡 API Reference

All endpoints are documented interactively at **http://localhost:8765/docs** (Swagger UI).

### `POST /upload`

Upload a PDF and start the extraction pipeline.

**Request:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | File (PDF) | ✅ | — | The PDF file to process |
| `force_ocr` | Boolean | ❌ | `true` | Enable OCR for scanned/image PDFs |
| `collection_name` | String | ❌ | auto | Custom ChromaDB collection name |

**Response (202):**
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

**Response:**
```json
{
  "status": "completed",
  "collection": "document",
  "pdf_name": "document.pdf",
  "outputs": {
    "markdown": "/home/.../output/document/extracted.md",
    "chunks": "/home/.../output/document/chunks.json",
    "chroma_collection": "document"
  },
  "stats": {
    "extract": { "chars": 154320, "time_s": 45.2 },
    "chunk": { "count": 327, "avg_chars": 472, "min_chars": 105, "max_chars": 3891, "time_s": 2.1 },
    "embed": { "collection": "document", "chunk_count": 327, "embed_time_s": 12.8 },
    "total_time_s": 60.1
  }
}
```

Status values: `processing`, `completed`, `error`.

### `GET /download/{job_id}/markdown`

Download the extracted markdown file.

- Returns: `text/markdown`
- Filename: `{collection_name}.md`

### `GET /download/{job_id}/chunks`

Download the chunks as JSON.

- Returns: `application/json`
- Filename: `{collection_name}_chunks.json`

### `GET /collections`

List all available ChromaDB collections.

**Response:**
```json
{
  "collections": [
    {
      "name": "document",
      "count": 327,
      "metadata": { "description": "RAG collection — 327 chunks" }
    }
  ],
  "chroma_dir": "/home/.../Arcwright/output/chroma_db"
}
```

### `POST /chat/{collection_name}`

Query a processed PDF via RAG (bonus feature for testing).

**Request:**
```json
{
  "query": "What is the main theme of chapter 3?",
  "top_k": 5
}
```

**Response:**
```json
{
  "query": "What is the main theme of chapter 3?",
  "collection": "document",
  "sources": [
    {
      "id": "doc_abc12345",
      "title": "Chapter 3: Structure",
      "section": "Part I: Foundations",
      "source": "my_document",
      "text": "The classical structure...",
      "distance": 0.2345
    }
  ],
  "total_found": 5
}
```

---

## 🖥️ Frontend Usage

### Upload Page (`/`)

1. **Drop Zone** — Drag & drop a PDF file or click to browse
2. **Processing** — Progress bar + status updates
3. **Job List** — Recent jobs listed on the left, click to view details
4. **Job Details** (right panel):
   - Pipeline statistics (chunks, time, extracted chars)
   - Download buttons for extracted markdown and chunks JSON
   - ChromaDB collection info
   - RAG Q&A panel for testing

### Collections Page (`/collections`)

- Lists all ChromaDB collections with chunk counts
- Shows the Python code snippet for accessing each collection
- Collections persist between API restarts

---

## 🐍 Python Library Usage

The `arcwright/` package can be imported directly from any Python script.

### Extract PDF

```python
from arcwright import extract

# Force OCR for scanned documents
markdown = extract.extract_pdf("path/to/book.pdf", force_ocr=True)
print(f"Extracted {len(markdown)} characters")
```

### Chunk Markdown

```python
from arcwright import chunk

chunks = chunk.chunk_markdown(markdown, source_name="My Book")
print(f"Generated {len(chunks)} chunks")
print(f"  Avg size: {sum(c['char_count'] for c in chunks) // len(chunks)} chars")
```

### Embed & Store

```python
from arcwright import embed

stats = embed.embed_and_store(chunks, collection_name="my_book")
print(f"Stored {stats['chunk_count']} chunks in ChromaDB")
```

### Full Pipeline

```python
from arcwright import pipeline

results = pipeline.run_pipeline(
    pdf_path="path/to/book.pdf",
    collection_name="my_book",
    force_ocr=True,
)

print(f"Status: {results['status']}")
print(f"Chunks: {results['stats']['chunk']['count']}")
print(f"Markdown: {results['outputs']['markdown']}")
```

### Access ChromaDB from External Projects

```python
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="/path/to/Arcwright/output/chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

# List collections
for c in client.list_collections():
    print(f"  {c.name}: {c.count()} chunks")

# Query a collection
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-m3")

collection = client.get_collection("my_book")
query_vec = model.encode(["What is the main theme?"])
results = collection.query(
    query_embeddings=query_vec.tolist(),
    n_results=5,
)

for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
    print(f"  [{meta['title']}] {doc[:200]}...")
```

---

## 📦 Output Formats

### extracted.md

Full markdown from the PDF with OCR. Structure preserved:
- Headings (`#`, `##`, `###`) maintained
- Paragraphs and lists preserved
- Tables converted to markdown format
- Images extracted as references

**Use for:** Reading, editing, manual review, feeding into other tools.

### chunks.json

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

**Use for:** LangChain, LlamaIndex, custom RAG systems, data analysis.

### ChromaDB Collection

Persistent vector database at `output/chroma_db/`. Each PDF gets its own collection with:
- 1024-dimensional BGE-M3 embeddings
- Metadata: title, section, source, char_count
- Collections survive API restarts

**Use for:** Direct programmatic access from any Python project.

---

## 🔍 OCR & Image-Based PDFs

Arwright uses **marker-pdf** with **Surya OCR** for PDF extraction.

| PDF Type | `force_ocr=true` (default) | `force_ocr=false` |
|----------|---------------------------|-------------------|
| **Digital PDF** (selectable text) | OCR still runs (slower but accurate) | Text extraction only (faster) |
| **Scanned PDF** (image-only) | OCR extracts text ✅ | ❌ Will produce empty output |
| **Mixed** (text + images) | OCR runs on everything | Text extracted, images skipped |

**Recommendation:** Keep `force_ocr=true` (default) for maximum compatibility.
The difference in processing time is negligible for most documents.

**First run notice:** marker-pdf downloads OCR models (~2GB) on first use. Subsequent runs use cached models.

---

## ❓ FAQ

### Does this need an internet connection?

Only for the **first run** (downloading embedding and OCR models ~4GB total).
After that, everything runs **completely offline**.

### Can I use this with other AI tools?

Yes! The ChromaDB collections are standard vector databases. Any Python project
with `chromadb` installed can connect directly:
```python
client = chromadb.PersistentClient(path="./output/chroma_db")
```

### What languages does the embedding support?

[BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) supports **100+ languages**
including English, Indonesian, Chinese, Arabic, and more. It's one of the top-ranked
multilingual embedding models on the [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard).

### How long does processing take?

| File Size | Digital PDF | Scanned (OCR) |
|-----------|-------------|---------------|
| 1 MB | ~10s | ~30s |
| 10 MB | ~30s | ~2min |
| 50 MB | ~2min | ~8min |

Times include model loading (first run adds ~30s for model downloads).

### Can I process multiple PDFs at once?

Currently each upload runs sequentially in a background thread. Multiple uploads
queue up and process one at a time. Each gets its own ChromaDB collection.

### How do I stop the server?

`Ctrl+C` in the terminal running the API. ChromaDB data is persisted on disk.

### Can I delete a collection?

Delete the collection via ChromaDB client:
```python
client.delete_collection("collection_name")
```
Or delete the entire `output/chroma_db/` directory (removes ALL collections).

---

## 🛠️ Development

### Running Tests

```bash
# Test Python package imports
source venv/bin/activate
cd ~/Arcwright
python -c "from arcwright import extract, chunk, embed, pipeline; print('✅ All imports OK')"

# Test API endpoints
curl http://localhost:8765/
curl http://localhost:8765/collections
```

### Modifying the Pipeline

The pipeline is modular — each step is a separate file:

| File | What to change |
|------|---------------|
| `arcwright/config.py` | Model names, chunk sizes, paths |
| `arcwright/extract.py` | OCR settings, PDF converter options |
| `arcwright/chunk.py` | Chunking strategy, sizes, metadata format |
| `arcwright/embed.py` | Batch size, embedding model, ChromaDB settings |
| `arcwright/pipeline.py` | Pipeline flow, error handling, output structure |

### Adding New Features

1. **New output format** → Add step in `arcwright/pipeline.py` + endpoint in `api/main.py`
2. **New embedding model** → Change `EMBEDDING_MODEL` in `arcwright/config.py`
3. **New frontend page** → Add route in `frontend/src/App.jsx` + new component in `components/`

---

## 📄 License

All components are open source:

| Component | License |
|-----------|---------|
| Arcwright (this project) | MIT |
| marker-pdf | MIT / GPL / Apache |
| BAAI/bge-m3 | MIT |
| ChromaDB | Apache 2.0 |
| FastAPI | MIT |
| React | MIT |
| Tailwind CSS | MIT |
| rank_bm25 | Apache 2.0 |

---

## 🤖 Project Configuration

This project uses **IBM Bob** as the primary development agent.
See [AGENTS.md](./AGENTS.md) for project instructions and [.bob/](./.bob/) for mode configuration.

---

*Built with ❤️ using open source tools.*
