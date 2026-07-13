"""
Semantic Refiner (Layer 5) — GPU-accelerated chunk refinement.

Uses BGE-M3 via CUDA to intelligently split oversized chunks
and merge semantically similar adjacent chunks.

Hardware: GPU 16GB VRAM (falls back to CPU if CUDA unavailable)
"""

import re
import time
import hashlib
from . import config


class SemanticRefiner:
    """
    GPU-accelerated semantic chunk refinement.
    
    Two core operations:
    1. split_oversized   — Split chunks > max_chars at topic boundaries
    2. merge_similar     — Merge adjacent chunks that cover the same topic
    
    Both use BGE-M3 embeddings + cosine similarity on the GPU.
    """
    
    _np = None  # lazy-loaded numpy
    
    def __init__(self, device: str = "auto", batch_size: int = None):
        """
        Initialize the refiner with BGE-M3 on the specified device.
        
        Args:
            device: "cuda", "cpu", or "auto" (auto-detect CUDA)
            batch_size: Embedding batch size (default: from config)
        """
        if batch_size is None:
            batch_size = config.REFINER_BATCH_SIZE
        self.batch_size = batch_size
        
        # ── Device detection ─────────────────────────────────
        if device == "auto":
            self._device = self._detect_device()
        else:
            self._device = device
        
        # ── Lazy-load model ─────────────────────────────────
        self._model = None
        print(f"  🔥 SemanticRefiner initialised (device={self._device})")
    
    @property
    def np(self):
        """Lazy-load numpy."""
        if self._np is None:
            import numpy as _np
            self._np = _np
        return self._np
    
    @property
    def model(self):
        """Lazy-load BGE-M3 on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"  📦 Loading BGE-M3 on {self._device}...")
            t0 = time.time()
            self._model = SentenceTransformer(
                config.EMBEDDING_MODEL,
                device=self._device,
            )
            print(f"  ✅ BGE-M3 loaded in {time.time()-t0:.1f}s")
        return self._model
    
    # ── Device Detection ─────────────────────────────────────
    
    @staticmethod
    def _detect_device() -> str:
        """Detect best available device."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"
    
    # ── Public API ───────────────────────────────────────────
    
    def refine_all(
        self,
        chunks: list,
        max_chars: int = None,
        split_threshold: float = None,
        merge_threshold: float = None,
        hard_max_chars: int = None,
    ) -> list:
        """
        Run full refinement pipeline:
        1. Split oversized chunks at topic boundaries
        2. Merge semantically similar adjacent chunks
        3. Recalculate metadata
        
        Args:
            chunks: List of chunk dicts from chunk_markdown()
            max_chars: Chars above which a chunk needs splitting
            split_threshold: Cosine sim below this = topic shift
            merge_threshold: Cosine sim above this = merge adjacent
            hard_max_chars: Absolute max after merging
        
        Returns:
            Refined list of chunk dicts
        """
        if max_chars is None:
            max_chars = config.CHUNK_MAX_CHARS
        if split_threshold is None:
            split_threshold = config.REFINER_SPLIT_THRESHOLD
        if merge_threshold is None:
            merge_threshold = config.REFINER_MERGE_THRESHOLD
        if hard_max_chars is None:
            hard_max_chars = config.CHUNK_HARD_MAX_CHARS
        
        t0 = time.time()
        n_before = len(chunks)
        
        # Step 1: Split oversized
        chunks = self.split_oversized(
            chunks, max_chars=max_chars, threshold=split_threshold
        )
        
        # Step 2: Merge similar adjacent
        chunks = self.merge_similar(
            chunks, threshold=merge_threshold, hard_max=hard_max_chars
        )
        
        # Step 3: Reset refiner flags
        for c in chunks:
            c["refiner_needed"] = False
        
        elapsed = time.time() - t0
        print(f"  ✅ Refined: {n_before} → {len(chunks)} chunks in {elapsed:.1f}s")
        
        return chunks
    
    # ── Split Oversized Chunks ───────────────────────────────
    
    def split_oversized(
        self,
        chunks: list,
        max_chars: int = None,
        threshold: float = None,
    ) -> list:
        """
        Split chunks that exceed max_chars at topic boundaries.
        
        Algorithm:
        1. Split chunk into sentences (by .!? + newlines)
        2. Sliding window of N sentences (stride=1)
        3. Embed each window via BGE-M3 (GPU)
        4. Cosine similarity between consecutive windows
        5. Where similarity drops below threshold = topic shift
        6. Split chunk at that point
        
        Args:
            chunks: List of chunk dicts
            max_chars: Threshold for triggering split
            threshold: Cosine similarity threshold for topic shift
        
        Returns:
            Refined list with oversized chunks split
        """
        if max_chars is None:
            max_chars = config.CHUNK_MAX_CHARS
        if threshold is None:
            threshold = config.REFINER_SPLIT_THRESHOLD
        
        # Collect all chunks that need splitting
        to_split = []
        keep = []
        for c in chunks:
            if c.get("refiner_needed", False) or c["char_count"] > max_chars:
                to_split.append(c)
            else:
                keep.append(c)
        
        if not to_split:
            return chunks
        
        print(f"  🔪 Splitting {len(to_split)} oversized chunks...")
        
        # Process each oversized chunk
        split_results = []
        for c in to_split:
            sub_chunks = self._split_one(c, max_chars, threshold)
            split_results.extend(sub_chunks)
        
        # Merge back with untouched chunks
        all_chunks = keep + split_results
        all_chunks.sort(key=lambda x: id(x))  # Stable-ish: preserve order
        
        return all_chunks
    
    def _split_one(
        self, chunk: dict, max_chars: int, threshold: float,
        hard_max: int = 2000,
    ) -> list:
        """Split a single oversized chunk at topic boundaries."""
        if hard_max is None:
            hard_max = config.CHUNK_HARD_MAX_CHARS
        text = chunk["text"]
        
        # If already under max, return as-is
        if len(text) <= max_chars:
            chunk["refiner_needed"] = False
            return [chunk]
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        # Edge case: too few sentences to analyze
        if len(sentences) < 6:
            # Force-split by sentence count even when too few sentences
            return self._force_split_by_size(chunk, sentences, hard_max)
        
        # Build sliding windows
        window_size = min(5, max(3, len(sentences) // 10))
        windows = []
        for i in range(len(sentences) - window_size + 1):
            windows.append(" ".join(sentences[i:i+window_size]))
        
        # Embed windows
        embeddings = self.model.encode(
            windows, show_progress_bar=False, batch_size=self.batch_size
        )
        
        # Compute similarity between consecutive windows
        sims = []
        for i in range(1, len(embeddings)):
            sim = float(self.np.dot(embeddings[i-1], embeddings[i]) / (
                self.np.linalg.norm(embeddings[i-1]) * self.np.linalg.norm(embeddings[i]) + 1e-10
            ))
            sims.append(sim)
        
        # Find breakpoints where similarity drops below threshold
        # Also ensure we don't create chunks smaller than min_chars
        breakpoints = [0]
        window_center = window_size // 2
        
        for i, sim in enumerate(sims):
            if sim < threshold:
                bp = i + window_center  # approximate sentence index
                # Check if this breakpoint creates a valid split
                if bp - breakpoints[-1] >= 2:  # at least 2 sentences
                    breakpoints.append(bp)
        
        breakpoints.append(len(sentences))
        
        # Build sub-chunks from semantic breakpoints
        sub_chunks = []
        for i in range(len(breakpoints) - 1):
            start = breakpoints[i]
            end = breakpoints[i + 1]
            sub_text = " ".join(sentences[start:end]).strip()
            
            if len(sub_text) < 50:
                continue  # skip empty/fragment chunks
            
            sub_chunk = {
                "id": f"{chunk['source'][:20]}_sem_{i}",
                "title": chunk["title"],
                "section": chunk["section"],
                "source": chunk["source"],
                "text": sub_text,
                "char_count": len(sub_text),
                "refiner_needed": False,
            }
            
            # Force-split if this sub-chunk still exceeds hard_max
            if len(sub_text) > hard_max:
                sub_sentences = self._split_sentences(sub_text)
                forced = self._force_split_chunk(chunk, sub_sentences, hard_max, f"force_{i}")
                sub_chunks.extend(forced)
            else:
                sub_chunks.append(sub_chunk)
        
        return sub_chunks if sub_chunks else self._force_split_by_size(chunk, sentences, hard_max)

    def _force_split_chunk(
        self, original_chunk: dict, sentences: list, hard_max: int, suffix: str
    ) -> list:
        """Force-split a list of sentences into chunks ≤ hard_max chars.
        Falls back to char-level split if a single sentence exceeds hard_max."""
        if not sentences:
            return []
        
        # Handle single sentence edge case
        if len(sentences) == 1:
            text = sentences[0].strip()
            if len(text) >= hard_max:
                return self._char_force_split(original_chunk, text, hard_max, suffix)
            if len(text) >= 50:
                sub_id = hashlib.md5(text[:100].encode()).hexdigest()[:8]
                return [{
                    "id": f"{original_chunk['source'][:20]}_{sub_id}",
                    "title": original_chunk["title"],
                    "section": original_chunk["section"],
                    "source": original_chunk["source"],
                    "text": text,
                    "char_count": len(text),
                    "refiner_needed": False,
                }]
            return []
        
        chunks = []
        current = []
        current_len = 0
        
        for sent in sentences:
            sent_stripped = sent.strip()
            sent_len = len(sent_stripped) + 1  # +1 for space
            
            # If a single sentence exceeds hard_max, char-split it inline
            if sent_len - 1 >= hard_max:
                # Flush current buffer first
                if current:
                    sub_text = " ".join(current).strip()
                    if len(sub_text) >= 50:
                        sub_id = hashlib.md5(sub_text[:100].encode()).hexdigest()[:8]
                        chunks.append({
                            "id": f"{original_chunk['source'][:20]}_{sub_id}",
                            "title": original_chunk["title"],
                            "section": original_chunk["section"],
                            "source": original_chunk["source"],
                            "text": sub_text,
                            "char_count": len(sub_text),
                            "refiner_needed": False,
                        })
                    current = []
                    current_len = 0
                # Char-split this monster sentence
                sub_chars = self._char_force_split(original_chunk, sent_stripped, hard_max, suffix)
                chunks.extend(sub_chars)
                continue
            
            if current_len + sent_len > hard_max and current:
                # Save current batch
                sub_text = " ".join(current).strip()
                if len(sub_text) >= 50:
                    sub_id = hashlib.md5(sub_text[:100].encode()).hexdigest()[:8]
                    chunks.append({
                        "id": f"{original_chunk['source'][:20]}_{sub_id}",
                        "title": original_chunk["title"],
                        "section": original_chunk["section"],
                        "source": original_chunk["source"],
                        "text": sub_text,
                        "char_count": len(sub_text),
                        "refiner_needed": False,
                    })
                current = [sent_stripped]
                current_len = sent_len
            else:
                current.append(sent_stripped)
                current_len += sent_len
        
        # Last batch
        if current:
            sub_text = " ".join(current).strip()
            if len(sub_text) >= 50:
                sub_id = hashlib.md5(sub_text[:100].encode()).hexdigest()[:8]
                chunks.append({
                    "id": f"{original_chunk['source'][:20]}_{sub_id}",
                    "title": original_chunk["title"],
                    "section": original_chunk["section"],
                    "source": original_chunk["source"],
                    "text": sub_text,
                    "char_count": len(sub_text),
                    "refiner_needed": False,
                })
        
        return chunks

    def _char_force_split(
        self, original_chunk: dict, text: str, hard_max: int, suffix: str
    ) -> list:
        """Last-resort char-level split for text that exceeds hard_max.
        Splits at the last sentence boundary before hard_max, or at hard_max char."""
        chunks = []
        while len(text) > hard_max:
            # Try to find a sentence boundary within range
            split_at = -1
            for boundary in ['. ', '! ', '? ', '.\n', '!\n', '?\n', '\n\n', '\n']:
                idx = text.rfind(boundary, 0, hard_max)
                if idx > hard_max // 2:  # At least half of max
                    split_at = idx + len(boundary)
                    break
            
            if split_at == -1:
                split_at = hard_max  # Hard cut at char limit
            
            piece = text[:split_at].strip()
            if len(piece) >= 50:
                sub_id = hashlib.md5(piece[:100].encode()).hexdigest()[:8]
                chunks.append({
                    "id": f"{original_chunk['source'][:20]}_{sub_id}",
                    "title": original_chunk["title"],
                    "section": original_chunk["section"],
                    "source": original_chunk["source"],
                    "text": piece,
                    "char_count": len(piece),
                    "refiner_needed": False,
                })
            text = text[split_at:].strip()
        
        # Remaining tail
        if len(text) >= 50:
            sub_id = hashlib.md5(text[:100].encode()).hexdigest()[:8]
            chunks.append({
                "id": f"{original_chunk['source'][:20]}_{sub_id}",
                "title": original_chunk["title"],
                "section": original_chunk["section"],
                "source": original_chunk["source"],
                "text": text,
                "char_count": len(text),
                "refiner_needed": False,
            })
        
        return chunks

    def _force_split_by_size(
        self, original_chunk: dict, sentences: list, hard_max: int
    ) -> list:
        """Legacy fallback: force-split into chunks ≤ hard_max chars."""
        if not sentences:
            return [original_chunk]
        if len(sentences) < 2:
            return [original_chunk]
        return self._force_split_chunk(original_chunk, sentences, hard_max, "fs")
    
    # ── Merge Similar Adjacent Chunks ────────────────────────
    
    def merge_similar(
        self,
        chunks: list,
        threshold: float = None,
        hard_max: int = None,
    ) -> list:
        """
        Merge adjacent chunks that are semantically similar.
        
        Algorithm:
        1. Embed all chunks via BGE-M3
        2. For each adjacent pair, compute cosine similarity
        3. If similarity > threshold AND combined size < hard_max → merge
        4. Repeat until no more merges possible
        
        Args:
            chunks: List of chunk dicts
            threshold: Cosine sim above this = merge
            hard_max: Combined chars must be below this
        
        Returns:
            Merged list
        """
        if threshold is None:
            threshold = config.REFINER_MERGE_THRESHOLD
        if hard_max is None:
            hard_max = config.CHUNK_HARD_MAX_CHARS
        
        if len(chunks) < 2:
            return chunks
        
        # Embed all chunks
        texts = [c["text"] for c in chunks]
        embeddings = self.model.encode(
            texts, show_progress_bar=False, batch_size=self.batch_size
        )
        
        # Find merge candidates
        merged = []
        skip_next = False
        
        for i in range(len(chunks)):
            if skip_next:
                skip_next = False
                continue
            
            if i < len(chunks) - 1:
                sim = float(self.np.dot(embeddings[i], embeddings[i+1]) / (
                    self.np.linalg.norm(embeddings[i]) * self.np.linalg.norm(embeddings[i+1]) + 1e-10
                ))
                
                combined_size = chunks[i]["char_count"] + chunks[i+1]["char_count"]

                if sim > threshold and combined_size + 2 <= hard_max:
                    # Merge
                    merged_text = chunks[i]["text"] + "\n\n" + chunks[i+1]["text"]
                    merged_id = hashlib.md5(merged_text[:100].encode()).hexdigest()[:8]
                    merged.append({
                        "id": f"{chunks[i]['source'][:20]}_{merged_id}",
                        "title": chunks[i]["title"],
                        "section": chunks[i]["section"],
                        "source": chunks[i]["source"],
                        "text": merged_text,
                        "char_count": len(merged_text),
                        "refiner_needed": False,
                    })
                    skip_next = True
                    continue
            
            merged.append(dict(chunks[i]))
            merged[-1]["refiner_needed"] = False
        
        if len(merged) < len(chunks):
            print(f"  🔗 Merged {len(chunks) - len(merged)} similar adjacent chunks")
        
        return merged
    
    # ── Coherence Scoring ────────────────────────────────────
    
    def compute_coherence(self, text: str) -> float:
        """
        Score how semantically coherent a chunk is.
        
        1.0 = perfectly coherent (single topic)
        0.0 = completely incoherent (random topics)
        
        Uses average pairwise cosine similarity between sentences.
        """
        sentences = self._split_sentences(text)
        if len(sentences) < 2:
            return 1.0
        
        embeddings = self.model.encode(
            sentences, show_progress_bar=False, batch_size=self.batch_size
        )
        
        # Average pairwise similarity
        sims = []
        for i in range(1, len(embeddings)):
            sim = float(self.np.dot(embeddings[i-1], embeddings[i]) / (
                self.np.linalg.norm(embeddings[i-1]) * self.np.linalg.norm(embeddings[i]) + 1e-10
            ))
            sims.append(sim)
        
        return float(self.np.mean(sims)) if sims else 1.0
    
    # ── Helpers ─────────────────────────────────────────────
    
    @staticmethod
    def _split_sentences(text: str) -> list:
        """Split text into sentences, handling common edge cases."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'«])', text)
        
        # Further split on paragraph boundaries within sentences
        result = []
        for s in sentences:
            # Split on newlines within a "sentence"
            parts = re.split(r'\n+', s)
            result.extend(p for p in parts if p.strip())
        
        # Filter very short fragments
        result = [s.strip() for s in result if len(s.strip()) > 10]
        
        return result if result else [text]
    
    @staticmethod
    def get_refiner_stats(chunks_before: list, chunks_after: list) -> dict:
        """Get statistics about the refinement process."""
        return {
            "chunks_before": len(chunks_before),
            "chunks_after": len(chunks_after),
            "split_count": max(0, sum(
                1 for c in chunks_before if c.get("refiner_needed", False)
            )),
            "merge_count": max(0, len(chunks_before) - len(chunks_after)),
        }
