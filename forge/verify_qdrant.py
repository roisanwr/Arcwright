#!/usr/bin/env python3
"""
Quick verification script for Arcwright Qdrant pipeline.
Run: python forge/verify_qdrant.py

Checks:
  1. Qdrant container running
  2. Collection exists and has data
  3. Retrieval works (BGE-M3 query → Qdrant search)
  4. 9Router/Gemini API accessible (for agent pipeline)
"""

import sys, time, json, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arcwright import config


def check(label: str, ok: bool, detail: str = ""):
    mark = "✅" if ok else "❌"
    print(f"  {mark} {label}" + (f"  |  {detail}" if detail else ""))


def main():
    print("=" * 60)
    print("  Arcwright — Pipeline Verification")
    print("=" * 60)

    # Track model for later reuse
    model = None

    # ── 1. Qdrant Health ──────────────────────────────────────
    print(f"\n1. Qdrant Docker @ {config.QDRANT_URL}")
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{config.QDRANT_URL}/healthz", timeout=5)
        data = resp.read().decode().strip()
        check("Qdrant running", True, data)
    except Exception as e:
        check("Qdrant running", False, str(e))

    # ── 2. Collection ─────────────────────────────────────────
    print(f"\n2. Collection '{config.QDRANT_COLLECTION}'")
    try:
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(url=config.QDRANT_URL)
        col_info = qdrant.get_collection(config.QDRANT_COLLECTION)
        check("Collection exists", True, f"{col_info.points_count} chunks, status={col_info.status}")

        if col_info.points_count > 0:
            # Sample 1 point
            sample = qdrant.query_points(
                collection_name=config.QDRANT_COLLECTION,
                query=[0.0] * 1024,
                limit=1,
                with_payload=True,
            )
            if sample.points:
                p = sample.points[0]
                src = p.payload.get("source", "?")
                title = p.payload.get("title", "?")
                text_len = len(p.payload.get("text", ""))
                check("Sample retrieval", True, f"source={src[:60]}, title={title[:60]}, text={text_len}ch")
        else:
            check("Has data", False, "0 chunks — run layer 7 first!")
    except Exception as e:
        check("Collection check", False, str(e))

    # ── 3. BGE-M3 Embedding Model ─────────────────────────────
    print(f"\n3. Embedding Model ({config.EMBEDDING_MODEL})")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(config.EMBEDDING_MODEL[:32])
        emb = model.encode(["Test query"], show_progress_bar=False)
        check("Model loads & encodes", True, f"dim={len(emb[0])}")
        # NOTE: model is reused in step 5 — do NOT delete
    except Exception as e:
        check("Model check", False, str(e))

    # ── 4. BGE-Reranker Model ────────────────────────────────
    print(f"\n4. Reranker Model ({config.RERANKER_MODEL})")
    try:
        from sentence_transformers import CrossEncoder
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        reranker = CrossEncoder(config.RERANKER_MODEL, max_length=512, device=device)
        scores = reranker.predict([["test", "hello world"]])
        check("Reranker loads & scores", True, f"device={device}, score={scores[0]:.4f}")
        del reranker
    except Exception as e:
        check("Reranker check", False, str(e))

    # ── 5. Full Pipeline: Query → Embed → Qdrant Search ──────
    print(f"\n5. Full Retrieval Pipeline")
    try:
        q = "How to make a compelling antagonist?"
        q_emb = model.encode([q], show_progress_bar=False)[0].tolist()
        results = qdrant.query_points(
            collection_name=config.QDRANT_COLLECTION,
            query=q_emb,
            limit=3,
            with_payload=True,
        )
        if results.points:
            for i, r in enumerate(results.points):
                src = r.payload.get("source", "?")[:50]
                score = r.score
                print(f"     #{i+1} score={score:.4f} | {src}")
            check("Retrieval works", True, f"{len(results.points)} results in top-3")
        else:
            check("Retrieval works", False, "no results")
    except Exception as e:
        check("Retrieval check", False, str(e))

    # ── 6. 9Router / Gemini API ──────────────────────────────
    print(f"\n6. LLM API (9Router → Gemini)")
    try:
        # Read from .env directly since forge config doesn't load_dotenv()
        from dotenv import load_dotenv
        load_dotenv()
        llm_url   = os.getenv("LLM_API_URL", "http://localhost:20128/v1")
        llm_key   = os.getenv("LLM_API_KEY", "sk-782161f8144ce425-lzjev3-4e325d13")
        llm_model = os.getenv("LLM_MODEL", "ag/gemini-3.1-pro-low")

        from openai import OpenAI
        client = OpenAI(api_key=llm_key, base_url=llm_url)
        resp = client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": "Say the word 'okay'"}],
            max_tokens=5,
            stream=False,
        )
        text = resp.choices[0].message.content.strip()
        check("API responds", True, f"reply='{text or '(empty but connected)'}'")
    except Exception as e:
        check("API check", False, str(e))

    # ── 7. Config Validation ─────────────────────────────────
    print(f"\n7. Config Sanity Check")
    print(f"     QDRANT_URL = {config.QDRANT_URL}")
    print(f"     QDRANT_COLLECTION = {config.QDRANT_COLLECTION}")
    print(f"     EMBEDDING_MODEL = {config.EMBEDDING_MODEL}")
    print(f"     LLM_API_URL = {config.LLM_API_URL}")
    print(f"     LLM_MODEL = {config.LLM_MODEL}")
    check("Config loads cleanly", True)

    # Cleanup GPU memory
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass

    print("\n" + "=" * 60)
    print("  Done. All green = pipeline ready to roll!")
    print("=" * 60)


if __name__ == "__main__":
    main()
