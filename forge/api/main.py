"""
Arwright API — FastAPI backend for PDF processing pipeline.
Free & open-source stack: FastAPI + ChromaDB + BGE-M3 + rank_bm25.
"""
import os
import sys
import json
import uuid
import time
import shutil
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for arcwright package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from arcwright.config import UPLOAD_DIR, OUTPUT_DIR, CHROMA_DIR, EMBEDDING_MODEL
from arcwright import pipeline as arkwright_pipeline
from arcwright import embed

# ─── App Setup ─────────────────────────────────────────────
from arcwright.extract import SUPPORTED_FORMATS

# Build supported formats string for docs
SUPPORTED_FMT_NAMES = ", ".join(
    f"`{ext}` ({name})" for ext, name in SUPPORTED_FORMATS.items()
)

app = FastAPI(
    title="Arwright Document Pipeline",
    description=f"Extract, chunk, embed any document — download results or query via RAG. Supports: {SUPPORTED_FMT_NAMES}",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory job tracking ────────────────────────────────
jobs = {}  # job_id → job status dict


# ─── Models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str
    top_k: int = 5


class ChatResponse(BaseModel):
    answer: str
    sources: list
    query: str


# ─── Background Pipeline Runner ────────────────────────────
def run_pipeline_job(job_id: str, pdf_path: str, collection_name: str, force_ocr: bool):
    """Run pipeline in background thread."""
    try:
        result = arkwright_pipeline.run_pipeline(
            pdf_path=pdf_path,
            collection_name=collection_name,
            force_ocr=force_ocr,
        )
        jobs[job_id] = {
            "status": result.get("status", "completed"),
            "collection": collection_name,
            "pdf_name": Path(pdf_path).name,
            "outputs": result.get("outputs", {}),
            "stats": result.get("stats", {}),
            "error": result.get("error"),
        }
    except Exception as e:
        jobs[job_id] = {
            "status": "error",
            "error": str(e),
        }


# ─── API Endpoints ─────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "Arwright Document Pipeline",
        "version": "1.1.0",
        "supported_formats": {k: v for k, v in SUPPORTED_FORMATS.items()},
        "docs": "/docs",
        "endpoints": {
            "upload": "POST /upload — Upload document (PDF, EPUB, MOBI, DOCX, TXT, HTML)",
            "status": "GET /status/{job_id} — Check processing status",
            "download_md": "GET /download/{job_id}/markdown — Download extracted markdown",
            "download_chunks": "GET /download/{job_id}/chunks — Download chunks JSON",
            "collections": "GET /collections — List all ChromaDB collections",
            "chat": "POST /chat/{collection_name} — Q&A (bonus)",
        },
    }


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(None),
    force_ocr: bool = Form(True),
):
    """
    Upload a document and start the extraction pipeline.
    The pipeline runs in the background — check /status/{job_id} for progress.

    Supported formats: PDF, EPUB, MOBI, AZW3, DOCX, TXT, HTML
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in SUPPORTED_FORMATS:
        supported = ", ".join(SUPPORTED_FORMATS.keys())
        raise HTTPException(
            400,
            f"Unsupported format '{ext}'. Supported: {supported}"
        )

    fmt_name = SUPPORTED_FORMATS.get(ext, ext)
    print(f"📥 Upload: {file.filename} ({fmt_name})")

    # Create job
    job_id = str(uuid.uuid4())[:8]
    safe_name = file.filename.replace(" ", "_")

    # Save uploaded file
    upload_path = UPLOAD_DIR / f"{job_id}_{safe_name}"
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Set collection name
    if collection_name is None:
        collection_name = Path(safe_name).stem
        collection_name = "".join(c for c in collection_name if c.isalnum() or c in "_")
        collection_name = collection_name[:50]

    # Track job
    jobs[job_id] = {
        "status": "processing",
        "filename": file.filename,
        "format": fmt_name,
        "collection": collection_name,
        "outputs": {},
        "stats": {},
    }

    # Start background pipeline
    thread = threading.Thread(
        target=run_pipeline_job,
        args=(job_id, str(upload_path), collection_name, force_ocr),
        daemon=True,
    )
    thread.start()

    return {
        "job_id": job_id,
        "filename": file.filename,
        "format": fmt_name,
        "collection": collection_name,
        "status": "processing",
        "check_status": f"/status/{job_id}",
    }


@app.get("/status/{job_id}")
def get_status(job_id: str):
    """Check the status of a pipeline job."""
    if job_id not in jobs:
        raise HTTPException(404, f"Job '{job_id}' not found")
    return jobs[job_id]


@app.get("/download/{job_id}/markdown")
def download_markdown(job_id: str):
    """Download the extracted markdown from a completed job."""
    if job_id not in jobs:
        raise HTTPException(404, f"Job '{job_id}' not found")
    
    job = jobs[job_id]
    md_path = job.get("outputs", {}).get("markdown")
    if not md_path or not os.path.exists(md_path):
        raise HTTPException(404, "Markdown file not found — job may still be processing")
    
    return FileResponse(
        md_path,
        filename=f"{job.get('collection', 'output')}.md",
        media_type="text/markdown",
    )


@app.get("/download/{job_id}/chunks")
def download_chunks(job_id: str):
    """Download the chunks JSON from a completed job."""
    if job_id not in jobs:
        raise HTTPException(404, f"Job '{job_id}' not found")
    
    job = jobs[job_id]
    chunks_path = job.get("outputs", {}).get("chunks")
    if not chunks_path or not os.path.exists(chunks_path):
        raise HTTPException(404, "Chunks file not found — job may still be processing")
    
    return FileResponse(
        chunks_path,
        filename=f"{job.get('collection', 'output')}_chunks.json",
        media_type="application/json",
    )


@app.get("/collections")
def list_collections():
    """List all available ChromaDB collections (reusable by other projects)."""
    collections = embed.list_collections()
    return {
        "collections": collections,
        "chroma_dir": str(CHROMA_DIR),
        "note": "Other Python projects can access ChromaDB directly at this path",
    }


@app.post("/chat/{collection_name}")
def chat(collection_name: str, req: ChatRequest):
    """
    Q&A — bonus feature to test RAG quality.
    Returns top-K relevant chunks for a query.
    Uses hybrid BM25 + Dense retrieval + reranking.
    """
    try:
        from sentence_transformers import SentenceTransformer, CrossEncoder
        import chromadb
        from chromadb.config import Settings
        import rank_bm25
        
        # Load models
        embed_model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Connect to ChromaDB
        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            collection = client.get_collection(collection_name)
        except Exception:
            raise HTTPException(404, f"Collection '{collection_name}' not found")
        
        # Embed query
        query_embedding = embed_model.encode([req.query])
        
        # Dense retrieval
        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=min(req.top_k * 2, 20),
        )
        
        # Format sources
        sources = []
        for i in range(len(results["ids"][0])):
            sources.append({
                "id": results["ids"][0][i],
                "title": results["metadatas"][0][i].get("title", ""),
                "section": results["metadatas"][0][i].get("section", ""),
                "source": results["metadatas"][0][i].get("source", ""),
                "text": results["documents"][0][i][:500],
                "distance": round(results["distances"][0][i], 4),
            })
        
        return {
            "query": req.query,
            "collection": collection_name,
            "sources": sources[:req.top_k],
            "total_found": len(sources),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Chat error: {e}")


# ─── Run ────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Arcwright API starting...")
    print(f"   Upload → /upload")
    print(f"   Status → /status/{{job_id}}")
    print(f"   Download → /download/{{job_id}}/markdown")
    print(f"   Download → /download/{{job_id}}/chunks")
    print(f"   Collections → /collections")
    print(f"   Chat → /chat/{{collection_name}}")
    print(f"   ChromaDB: {CHROMA_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8765)
