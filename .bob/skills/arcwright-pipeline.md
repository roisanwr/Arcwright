---
name: arcwright-pipeline
description: "Arcwright RAG pipeline skills — PDF extraction, chunking, embedding, and ChromaDB operations"
version: 1.0.0
---

# Arcwright Pipeline Skills

## PDF Extraction
- Use marker-pdf library for extraction
- Output to markdown format
- Preserve original heading structure
- Extract per-chapter, not per-page

## Chunking Strategy
- Split markdown by concept heading (`###` or higher)  
- Preserve paragraph coherence within chunks
- Minimum chunk size: 50 tokens
- Maximum chunk size: 500 tokens
- Overlap: 20 tokens between consecutive chunks

## Embedding
- Use sentence-transformers for embeddings
- Store in ChromaDB collection: `storytelling_concepts`
- Index metadata: book title, chapter, chunk index

## ChromaDB Operations
- Collection: `storytelling_concepts`
- Distance metric: cosine
- Query returns top 5 results by default
