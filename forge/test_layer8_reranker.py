#!/usr/bin/env python3
"""
Layer 8: Retrieval & Reranking (BGE-Reranker)
Tests querying the ChromaDB and reranking the results using CrossEncoder.
"""
import os, sys, time, argparse
from pathlib import Path
import torch

# Setup paths
sys.path.insert(0, str(Path(__file__).resolve().parent))
from arcwright import config
from arcwright.embed import get_embedding_model, get_chroma_client

def retrieve_and_rerank(query: str, top_k: int = 3, fetch_k: int = 20):
    print("="*70)
    print(f"🔍 QUERY: '{query}'")
    print("="*70)
    
    # 1. Embed Query
    print("\n🧠 1. Loading embedding model (BAAI/bge-m3)...")
    embed_model = get_embedding_model("BAAI/bge-m3")
    query_emb = embed_model.encode([query], show_progress_bar=False)[0].tolist()
    
    # 2. Retrieve from ChromaDB
    print(f"📚 2. Fetching top {fetch_k} raw results from ChromaDB...")
    client = get_chroma_client()
    collection = client.get_collection("storytelling_books")
    
    t0 = time.time()
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=fetch_k
    )
    t_chroma = time.time() - t0
    print(f"  ✅ Retrieved in {t_chroma:.3f}s")
    
    docs = results['documents'][0]
    metadatas = results['metadatas'][0]
    ids = results['ids'][0]
    distances = results['distances'][0]
    
    # 3. Rerank
    print("\n⚖️  3. Loading Reranker model (BAAI/bge-reranker-v2-m3)...")
    from sentence_transformers import CrossEncoder
    device = "cuda" if torch.cuda.is_available() else "cpu"
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512, device=device)
    
    pairs = [[query, doc] for doc in docs]
    
    print(f"  🔄 Scoring {fetch_k} chunk-query pairs on {device.upper()}...")
    t1 = time.time()
    scores = reranker.predict(pairs)
    t_rerank = time.time() - t1
    print(f"  ✅ Reranked in {t_rerank:.3f}s")
    
    # Combine and sort
    ranked_results = []
    for i in range(len(docs)):
        ranked_results.append({
            "id": ids[i],
            "text": docs[i],
            "metadata": metadatas[i],
            "chroma_dist": distances[i],
            "rerank_score": float(scores[i]),
            "original_rank": i + 1
        })
        
    # Sort by rerank score descending (higher is better)
    ranked_results.sort(key=lambda x: x["rerank_score"], reverse=True)
    
    # 4. Display
    print("\n" + "="*70)
    print(f"🏆 TOP {top_k} RESULTS AFTER RERANKING")
    print("="*70)
    for i, res in enumerate(ranked_results[:top_k]):
        meta = res['metadata']
        print(f"#{i+1} | Score: {res['rerank_score']:.2f} | 📈 Jumped from raw rank #{res['original_rank']}")
        print(f"📚 Book:  {meta.get('source', 'Unknown')}")
        print(f"📌 Title: {meta.get('title', 'Unknown')}")
        
        # Show chunk context if it exists
        text = res['text']
        context_split = text.split('\n\n', 1)
        if len(context_split) > 1 and context_split[0].startswith('['):
            print(f"🧠 Ctx:   {context_split[0]}")
            body = context_split[1]
        else:
            body = text
            
        text_preview = body[:400].replace('\n', ' ') + "..."
        print(f"📝 Text:  {text_preview}")
        print("-" * 70)
        
    # Clear memory
    del embed_model
    del reranker
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="How to make an antagonist or villain more compelling?", help="Search query")
    parser.add_argument("--fetch", type=int, default=20, help="Number of chunks to fetch from DB")
    parser.add_argument("--top", type=int, default=3, help="Number of chunks to show after reranking")
    args = parser.parse_args()
    
    retrieve_and_rerank(args.query, args.top, args.fetch)
