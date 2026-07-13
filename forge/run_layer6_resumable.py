#!/usr/bin/env python3
"""
Layer 6: Contextual Enhancer — Resumable Version
Saves progress per batch, resumes from last completed batch on restart.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

# Add forge to path
sys.path.insert(0, str(Path(__file__).parent))

from arcwright import config
from arcwright.enhancer import ContextualEnhancer
import arcwright.utils.llm as llm_module


def patch_llm_for_9router(api_url: str, api_key: str, model: str):
    """Patch the LLM module to force stream=False for 9Router."""
    original_call = llm_module._call

    def patched_call(prompt, system=None):
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=api_url,
        )
        messages = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.append({'role': 'user', 'content': prompt})

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=200,
            stream=False,  # FORCE NON-STREAMING FOR 9ROUTER
        )
        return resp.choices[0].message.content.strip()

    llm_module._call = patched_call
    print(f"  🔧 Patched LLM for 9Router: {api_url} / {model}")


def get_progress_file(output_dir: Path, target: str) -> Path:
    """Get path to progress tracking file."""
    return output_dir / target / "layer6_progress.json"


def load_progress(output_dir: Path, target: str) -> dict:
    """Load existing progress or return empty state."""
    pf = get_progress_file(output_dir, target)
    if pf.exists():
        with open(pf) as f:
            data = json.load(f)
    else:
        data = {}

    # Ensure all fields exist
    defaults = {
        "target": target,
        "total_chunks": 0,
        "completed_batches": [],
        "last_batch_idx": -1,
        "enhanced_chunks": [],
        "started_at": None,
        "updated_at": None,
        "config_history": [],
        "batch_configs": {},
    }
    for k, v in defaults.items():
        if k not in data:
            data[k] = v

    return data


def save_progress(output_dir: Path, target: str, progress: dict):
    """Save progress to file atomically."""
    pf = get_progress_file(output_dir, target)
    pf.parent.mkdir(parents=True, exist_ok=True)
    progress["updated_at"] = time.time()
    # Atomic write
    tmp = pf.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(progress, f, indent=2)
    tmp.replace(pf)


def save_enhanced_chunks(output_dir: Path, target: str, chunks: list):
    """Save enhanced chunks to final output file."""
    out = output_dir / target / "chunks_enhanced.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"  💾 Saved {len(chunks)} enhanced chunks to {out}")


def enhance_with_resume(
    target: str,
    batch_size: int = 10,
    api_url: str = None,
    api_key: str = None,
    model: str = None,
):
    """Main enhancement function with resume capability."""

    base = config.OUTPUT_DIR
    target_dir = base / target

    # Load refined chunks
    refined_file = target_dir / "chunks_refined.json"
    if not refined_file.exists():
        print(f"❌ File not found: {refined_file}")
        sys.exit(1)

    with open(refined_file) as f:
        chunks = json.load(f)

    # Load cleaned text for summary
    clean_file = target_dir / "cleaned.md"
    with open(clean_file) as f:
        full_text = f.read()

    print(f"📚 Loaded {len(chunks)} chunks, {len(full_text):,} chars")
    print(f"🎯 Target: {target}")
    print(f"⚙️  Batch size: {batch_size}")

    # Load progress
    progress = load_progress(base, target)
    progress["total_chunks"] = len(chunks)

    if progress["started_at"] is None:
        progress["started_at"] = time.time()

    # Track current config
    current_config = {
        "api_url": api_url,
        "model": model,
        "batch_size": batch_size,
    }

    # Check if config changed from last run
    config_history = progress.get("config_history", [])
    if config_history:
        last_config = config_history[-1]
        if last_config != current_config:
            print(f"⚠️  Config changed since last run!")
            print(f"   Last: {last_config}")
            print(f"   Now:  {current_config}")
            print(f"   → Completed batches with OLD config will be KEPT")
            print(f"   → Remaining batches will use NEW config")
            # Don't auto-reset, let user decide with --reset flag

    # Calculate batch info
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    completed_batches = set(progress["completed_batches"])
    last_completed = progress["last_batch_idx"]

    print(f"📊 Progress: {len(completed_batches)}/{total_batches} batches done")
    if completed_batches:
        print(f"   ✅ Completed batches: {sorted(completed_batches)}")

    # Start with existing enhanced chunks if any
    enhanced_chunks = progress["enhanced_chunks"].copy()

    # Patch LLM if custom API provided
    if api_url and api_key and model:
        patch_llm_for_9router(api_url, api_key, model)
        config.USE_LLM = True

    if not config.USE_LLM:
        print("  ⏭️  LLM not configured — skipping enhancement")
        return chunks

    # Create enhancer
    enhancer = ContextualEnhancer(batch_size=batch_size)

    # Generate document summary (only once, reuse if cached)
    print(f"  📝 Generating document summary...")
    summary = enhancer._get_summary(full_text)
    if not summary:
        print("  ⚠️  Summary generation failed — skipping enhancement")
        return chunks
    print(f"  ✅ Summary: {summary[:100]}...")

    # Process batches
    t0 = time.time()

    for batch_idx in range(total_batches):
        if batch_idx in completed_batches:
            # Skip already completed batch
            continue

        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(chunks))
        batch = chunks[start_idx:end_idx]

        print(f"\n  🌟 Batch {batch_idx + 1}/{total_batches} (chunks {start_idx}-{end_idx - 1})...")

        # Enhance this batch
        batch_enhanced = enhancer._enhance_batch(batch, summary)

        # Store enhanced chunks in progress
        for i, ec in enumerate(batch_enhanced):
            global_idx = start_idx + i
            # Ensure list is large enough
            while len(enhanced_chunks) <= global_idx:
                enhanced_chunks.append(None)
            enhanced_chunks[global_idx] = ec

        # Mark batch complete
        completed_batches.add(batch_idx)
        progress["completed_batches"] = sorted(completed_batches)
        progress["last_batch_idx"] = batch_idx
        progress["enhanced_chunks"] = [c for c in enhanced_chunks if c is not None]

        # Track which config was used for this batch
        if "batch_configs" not in progress:
            progress["batch_configs"] = {}
        progress["batch_configs"][str(batch_idx)] = current_config

        # Save progress after each batch
        progress["config_history"] = config_history + [current_config] if not config_history else config_history
        # Only add current config if not already the last one
        if not progress["config_history"] or progress["config_history"][-1] != current_config:
            progress["config_history"].append(current_config)
        save_progress(base, target, progress)

        # Progress stats
        elapsed = time.time() - t0
        done = len(completed_batches)
        pct = done / total_batches * 100
        eta = (elapsed / done) * (total_batches - done) if done > 0 else 0
        print(f"     ✅ Batch {batch_idx + 1} done | {done}/{total_batches} ({pct:.1f}%) | ETA: {eta:.0f}s")

    # All batches done - finalize
    print(f"\n🎉 All {total_batches} batches complete!")
    final_enhanced = [c for c in enhanced_chunks if c is not None]

    # Save final output
    save_enhanced_chunks(base, target, final_enhanced)

    # Clean up progress file (optional - keep for audit)
    # pf = get_progress_file(base, target)
    # if pf.exists():
    #     pf.unlink()

    # Stats
    n_ctx = sum(1 for c in final_enhanced if c.get("_context"))
    total_time = time.time() - progress["started_at"]
    print(f"\n📊 Final Stats:")
    print(f"   Chunks: {len(final_enhanced)}")
    print(f"   Enhanced: {n_ctx} ({n_ctx/len(final_enhanced)*100:.1f}%)")
    print(f"   Time: {total_time:.0f}s ({total_time/60:.1f} min)")

    return final_enhanced


def main():
    parser = argparse.ArgumentParser(description="Layer 6: Contextual Enhancer (Resumable)")
    parser.add_argument("target", help="Target directory name (e.g., refined_storyworthy)")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for LLM calls")
    parser.add_argument("--api-url", default=os.environ.get("LLM_API_URL"), help="LLM API base URL")
    parser.add_argument("--api-key", default=os.environ.get("LLM_API_KEY"), help="LLM API key")
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL"), help="LLM model name")
    parser.add_argument("--reset", action="store_true", help="Ignore progress and start fresh")

    args = parser.parse_args()

    # Handle reset
    if args.reset:
        pf = get_progress_file(config.OUTPUT_DIR, args.target)
        if pf.exists():
            pf.unlink()
            print(f"🗑️  Cleared progress file: {pf}")

    enhance_with_resume(
        target=args.target,
        batch_size=args.batch_size,
        api_url=args.api_url,
        api_key=args.api_key,
        model=args.model,
    )


if __name__ == "__main__":
    main()