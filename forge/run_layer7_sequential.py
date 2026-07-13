#!/usr/bin/env python3
"""
Layer 7: Sequential Embedding (BGE-M3 on GPU)
Processes one book at a time to avoid OOM.
"""

import sys, json, time, torch
from pathlib import Path

# Setup
sys.path.insert(0, str(Path(__file__).parent))
from arcwright import config
from arcwright.embed import get_embedding_model, get_chroma_client, embed_and_store

# Config
COLLECTION = "storytelling_books"
CHROMA_DIR = config.CHROMA_DIR
BATCH_SIZE = 200

# Books to process (in order - largest first for progress visibility)
BOOKS = [
    "refined_the_anatomy_of_story_22_steps_to_becoming_a_master",
    "refined_how_to_tell_a_story", 
    "refined_robert_mckee_story",
    "refined_the_hero_with_a_thousand_faces_commemorative_editi",
    "refined_on_writing_a_memoir_of_the_craft",
    "refined_power_of_myth",
    "refined_story_genius",
    "refined_storyworthy",
    "refined_the_writers_journey_mythic_structure_for_writers",
    "refined_the_storytellers_secret_from_ted_speakers_to_busi",
    "refined_into_the_woods_a_five_act_journey_into_sto",
    "refined_contagious_why_things_catch_on",
    "refined_building_a_storybrand_2_0_clarify_your_mes",
    "refined_wired_for_story",
    "refined_talk_like_ted_the_9_public_speaking_secret",
    "refined_ted_talks",
    "refined_storytelling_with_data",
    "refined_save_the_cat_the_last_book_on_screenwritin",
    "refined_resonate_present_visual_stories_that_transform_aud",
    "refined_storytelling_animal",
    "refined_steering_the_craft_a_twenty_first_century_guide_to",
    "refined_writing_down_the_bones",
    "refined_truth_in_comedy",
    "refined_pixar_storytelling_rules_for_effective_sto",
    "refined_the_science_of_storytelling",
    "refined_the_elements_of_style_2011_revised_edition",
]

def process_book(book_dir_name: str, model) -> dict:
    """Embed a single book's chunks."""
    output_dir = config.OUTPUT_DIR / book_dir_name
    chunks_file = output_dir / "chunks_enhanced.json"
    
    if not chunks_file.exists():
        return {"book": book_dir_name, "status": "skipped", "reason": "no chunks_enhanced.json"}
    
    with open(chunks_file) as f:
        chunks = json.load(f)
    
    if not chunks:
        return {"book": book_dir_name, "status": "skipped", "reason": "empty chunks"}
    
    # Fix duplicate IDs within book by adding index suffix
    seen = {}
    for i, c in enumerate(chunks):
        base_id = c["id"]
        if base_id in seen:
            seen[base_id] += 1
            c["id"] = f"{book_dir_name}_{base_id}_{seen[base_id]}"
        else:
            seen[base_id] = 0
            c["id"] = f"{book_dir_name}_{base_id}"
    
    print(f"\n📖 [{book_dir_name}] {len(chunks)} chunks")
    
    start = time.time()
    try:
        stats = embed_and_store(
            chunks=chunks,
            collection_name="storytelling_books",
            embed_model=model,
            chroma_dir=str(CHROMA_DIR),
            replace=False,  # append
        )
        elapsed = time.time() - start
        return {
            "book": book_dir_name,
            "status": "success",
            "chunks": stats.get("new_count", 0),
            "total_in_collection": stats.get("chunk_count", 0),
            "time_s": round(elapsed, 1),
        }
    except Exception as e:
        return {
            "book": book_dir_name,
            "status": "error",
            "error": str(e),
            "time_s": round(time.time() - start, 1),
        }

def main():
    print("="*60)
    print("🚀 Layer 7: Sequential Embedding (BGE-M3 on GPU)")
    print("="*60)
    
    # GPU check
    if not torch.cuda.is_available():
        print("❌ CUDA not available!")
        sys.exit(1)
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Load model ONCE
    print("\n🧠 Loading BGE-M3 model...")
    model = get_embedding_model("BAAI/bge-m3")
    print(f"Model device: {model.device}")
    print(f"Dim: {model.get_sentence_embedding_dimension()}")
    
    # Process each book
    results = []
    total_chunks = 0
    total_time = 0
    
    for i, book in enumerate(BOOKS, 1):
        print(f"\n{'='*60}")
        print(f"📚 Book {i}/{len(BOOKS)}: {book}")
        print(f"{'='*60}")
        
        result = process_book(book, model)
        results.append(result)
        
        if result["status"] == "success":
            total_chunks += result["chunks"]
            total_time += result["time_s"]
            print(f"  ✅ {result['chunks']} chunks in {result['time_s']:.1f}s")
            print(f"  Collection now: {result['total_in_collection']} chunks")
        elif result["status"] == "skipped":
            print(f"  ⏭️  Skipped: {result['reason']}")
        else:
            print(f"  ❌ Error: {result.get('error', 'Unknown')}")
        
        # Clear cache between books
        torch.cuda.empty_cache()
    
    # Summary
    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    success = sum(1 for r in results if r["status"] == "success")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "error")
    
    for r in results:
        status = "✅" if r["status"] == "success" else "⏭️" if r["status"] == "skipped" else "❌"
        chunks = r.get("chunks", 0)
        print(f"  {status} {r['book']}: {chunks} chunks")
    
    print(f"\nTotal: {success} success, {skipped} skipped, {failed} failed")
    print(f"Total chunks embedded: {total_chunks}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} min)")

if __name__ == "__main__":
    main()