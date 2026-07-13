"""
Contextual Enhancer (Layer 6) — adds position context to chunks via LLM.

Inspired by Anthropic's Contextual Retrieval technique.
Each chunk gets a short description of its position and role in the
document, which is prepended before embedding. This dramatically
improves retrieval accuracy for chunks that need surrounding context.

Pipeline position: after chunking/refinement, before embedding.

Usage:
    enhancer = ContextualEnhancer()
    enhanced = enhancer.enhance_all(chunks, full_text)
    # enhanced[i]["text"] == "[CONTEXT] ... \\n\\n original chunk text"
"""

import re
import time
from . import config
from .utils import llm


# ─── Prompts ─────────────────────────────────────────────

SUMMARY_SYSTEM = "You are a precise document summarizer. Output only the summary, no meta-commentary."

SUMMARY_PROMPT = """Summarize this document in 2-3 sentences. Capture:
1. The main topic/purpose
2. The structure (chapters, sections)
3. The narrative arc or argument flow

DOCUMENT (first 3000 chars):
{preview}

DOCUMENT (last 1000 chars):
{tail}

SUMMARY:"""


ENHANCE_SYSTEM = """You are a context enhancer for a RAG retrieval system.
Your task: given a document summary and a chunk of text, generate ONE sentence
that explains where this chunk fits in the document and what it's about.

Rules:
- Output ONLY the context sentence, nothing else
- Start with the section/chapter reference if identifiable
- Be specific but concise (max 40 words)
- Do NOT repeat text from the chunk verbatim
- Do NOT use phrases like "This chunk discusses" or "In this passage"
"""

ENHANCE_PROMPT = """DOCUMENT SUMMARY: {summary}

CHUNK TEXT: "{chunk_text}"

Generate one context sentence in this format:
"[SECTION REFERENCE] — Brief context of what this chunk contains and its role."

Examples:
- "[Chapter 3: The Grief] — Protagonist John processes his wife's death, still in denial phase."
- "[Part II, Section A] — Introduction of the mentor character who will guide the hero's journey."
- "[Appendix: Timeline] — Chronological list of key events in the story, referenced throughout."

CONTEXT SENTENCE:"""


class ContextualEnhancer:
    """
    Adds position context to chunks using LLM.
    
    Two-step process:
    1. Generate document summary (1 LLM call)
    2. Enhance each chunk with context (batched, N chunks per call)
    
    When LLM is unavailable, returns chunks unchanged.
    """
    
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self._summary = None
    
    # ── Public API ─────────────────────────────────────────
    
    def enhance_all(self, chunks: list, full_text: str) -> list:
        """
        Enhance all chunks with context.
        
        Args:
            chunks: List of chunk dicts from chunk_markdown() or refiner
            full_text: The complete cleaned markdown text
        
        Returns:
            Chunks with context prepended to .text and ._context field added
        """
        if not config.USE_LLM:
            print("  ⏭️  LLM not configured — skipping context enhancement")
            return chunks
        
        if not chunks:
            return chunks
        
        t0 = time.time()
        n = len(chunks)
        
        # Step 1: Generate global summary
        print(f"  📝 Generating document summary...")
        summary = self._get_summary(full_text)
        if not summary:
            print("  ⚠️  Summary generation failed — skipping enhancement")
            return chunks
        
        # Step 2: Enhance chunks in batches
        print(f"  🌟 Enhancing {n} chunks with context (batch_size={self.batch_size})...")
        enhanced = []
        
        for i in range(0, n, self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_enhanced = self._enhance_batch(batch, summary)
            enhanced.extend(batch_enhanced)
            
            # Progress
            done = min(i + self.batch_size, n)
            print(f"     {done}/{n} chunks enhanced", end="\r")
        
        print(f"\n  ✅ Enhancement done in {time.time()-t0:.1f}s — {n} chunks")
        
        return enhanced
    
    # ── Internal: Summary ──────────────────────────────────
    
    def _get_summary(self, full_text: str) -> str:
        """Generate or return cached document summary."""
        if self._summary:
            return self._summary
        
        preview = full_text[:3000]
        tail = full_text[-1000:]
        
        prompt = SUMMARY_PROMPT.format(preview=preview, tail=tail)
        summary = llm.llm_complete(prompt, system=SUMMARY_SYSTEM)
        
        if summary:
            self._summary = summary
        else:
            # Fallback: extract first meaningful paragraph
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            heading = next((l for l in lines if l.startswith('#')), full_text[:200])
            self._summary = heading[:300]
        
        return self._summary
    
    # ── Internal: Batch Enhance ────────────────────────────
    
    def _enhance_batch(self, chunks: list, summary: str) -> list:
        """Enhance a batch of chunks in a single LLM call."""
        enhanced = []
        
        for chunk in chunks:
            context = self._get_context_for_chunk(chunk, summary)
            
            # Create enhanced chunk
            enhanced_chunk = dict(chunk)
            enhanced_chunk["_context"] = context
            
            if context:
                enhanced_chunk["text"] = context + "\n\n" + chunk["text"]
                enhanced_chunk["char_count"] = len(enhanced_chunk["text"])
            
            enhanced.append(enhanced_chunk)
        
        return enhanced
    
    def _get_context_for_chunk(self, chunk: dict, summary: str) -> str:
        """Generate context for a single chunk via LLM."""
        chunk_text = chunk["text"][:600]  # First 600 chars is enough for context
        if len(chunk_text) < 20:
            return ""
        
        prompt = ENHANCE_PROMPT.format(
            summary=summary,
            chunk_text=chunk_text,
        )
        
        context = llm.llm_complete(prompt, system=ENHANCE_SYSTEM)
        
        if context and len(context) > 10:
            return context.strip()
        
        # Fallback: use heading info
        title = chunk.get("title", "")
        section = chunk.get("section", "")
        if title and section:
            return f"[{section}: {title}]"
        elif title:
            return f"[{title}]"
        
        return ""
    
    # ── Stats ──────────────────────────────────────────────
    
    @staticmethod
    def get_enhancer_stats(chunks_before: list, chunks_after: list) -> dict:
        """Get statistics about the enhancement process."""
        n_context = sum(1 for c in chunks_after if c.get("_context"))
        avg_context_len = (
            sum(len(c["_context"]) for c in chunks_after if c.get("_context"))
            // max(n_context, 1)
        )
        
        return {
            "chunks_in": len(chunks_before),
            "chunks_out": len(chunks_after),
            "enhanced": n_context,
            "enhanced_pct": round(n_context / max(len(chunks_after), 1) * 100, 1),
            "avg_context_len": avg_context_len,
        }
