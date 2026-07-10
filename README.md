# Arcwright — PDF Pipeline

Extract, chunk, embed any PDF. Download results or query via RAG.
All **free & open-source** — no API keys needed.

## Features
- 📄 **Upload any PDF** — drag & drop
- 🔍 **OCR** for scanned/image-based PDFs (marker-pdf)
- ✂️ **Semantic chunking** by heading structure
- 🧠 **BGE-M3 embeddings** (1024-dim, multilingual)
- 🗄️ **ChromaDB** vector storage
- 📥 **Download** extracted markdown + chunks JSON
- 🧪 **Test RAG** with Q&A interface
- 🔗 **Reusable** — ChromaDB collections accessible from any Python project

## Tech Stack
| Component | Tech | License |
|-----------|------|---------|
| Backend | FastAPI + Uvicorn | MIT |
| Frontend | React + Vite + Tailwind | MIT |
| PDF Extraction | marker-pdf | MIT/GPL/Apache |
| Embeddings | BAAI/bge-m3 (sentence-transformers) | MIT |
| Vector DB | ChromaDB | Apache 2.0 |
| Hybrid Search | rank_bm25 | Apache 2.0 |

## Quick Start

### Backend
```bash
source venv/bin/activate
python api/main.py
# → http://localhost:8765
# → API docs: http://localhost:8765/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload PDF (multipart/form-data) |
| `/status/{job_id}` | GET | Check processing status |
| `/download/{job_id}/markdown` | GET | Download extracted markdown |
| `/download/{job_id}/chunks` | GET | Download chunks JSON |
| `/collections` | GET | List all ChromaDB collections |
| `/chat/{collection_name}` | POST | Q&A (test RAG quality) |

## Outputs
- **extracted.md** — Full text from PDF with OCR
- **chunks.json** — Structured chunks with metadata
- **ChromaDB collection** — Vector embeddings, queryable from Python

## Python Usage (Other Projects)
```python
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="path/to/arcwright/output/chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

collection = client.get_collection("your_collection_name")
results = collection.query(...)
```
