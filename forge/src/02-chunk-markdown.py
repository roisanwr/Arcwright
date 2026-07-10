#!/usr/bin/env python3
"""
Step 2: Chunk markdown per konsep (heading-based chunking)
Output: JSON array of chunks with metadata
"""
import re
import json
import os
from pathlib import Path

MARKDOWN_PATH = os.path.expanduser("~/rag-storytelling-output/Robert McKee - Story (pdf).md")
CHUNKS_OUTPUT = os.path.expanduser("~/rag-storytelling-output/chunks.json")

BOOK_TITLE = "Story: Substance, Structure, Style, and the Principles of Screenwriting"
BOOK_AUTHOR = "Robert McKee"

with open(MARKDOWN_PATH, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")

# Parse the markdown into a heading tree
chunks = []
current_part = ""       # # title (Part)
current_chapter = ""    # ## chapter
current_concept = ""    # ### concept
current_text = []

def save_chunk():
    """Save accumulated text as a chunk."""
    global current_text
    text = "\n".join(current_text).strip()
    # Skip empty or too-short chunks
    if len(text) < 50:
        current_text = []
        return
    
    # Skip chunks that are just images or navigation
    if text.count("![](") > len(text) * 0.1:
        current_text = []
        return
    
    # Combine context for the chunk title
    if current_concept:
        title = current_concept
        section = current_chapter if current_chapter else current_part
    elif current_chapter:
        title = current_chapter
        section = current_part
    else:
        title = current_part
        section = ""
    
    # Clean title (remove bold markers that are used in headings)
    title_clean = re.sub(r'\*\*', '', title)
    section_clean = re.sub(r'\*\*', '', section)
    
    chunks.append({
        "id": f"mckee-{len(chunks):04d}",
        "title": title_clean,
        "section": section_clean,
        "book": BOOK_TITLE,
        "author": BOOK_AUTHOR,
        "text": text,
        "char_count": len(text),
    })
    current_text = []

for line in lines:
    # Check for headings
    heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
    
    if heading_match:
        # Save previous chunk before starting new one
        save_chunk()
        
        level = len(heading_match.group(1))
        heading_text = heading_match.group(2).strip()
        
        if level == 1:
            current_part = heading_text
            current_chapter = ""
            current_concept = ""
            # Level 1 headings are book parts - don't chunk these alone
            current_text = [line]
        elif level == 2:
            current_chapter = heading_text
            current_concept = ""
            current_text = [line]
        elif level == 3:
            current_concept = heading_text
            current_text = [line]
        else:  # level 4
            # Level 4 headings - include in current concept or create standalone
            current_text.append(line)
    else:
        current_text.append(line)

# Save the last chunk
save_chunk()

# Filter out chunks that are too big (likely whole chapters that weren't split properly)
# and chunks that are table of contents
chunks = [c for c in chunks if c["char_count"] < 8000]
chunks = [c for c in chunks if "CONTENTS" not in c.get("section", "") or c["title"] != "CONTENTS"]

# Stats
print(f"Total chunks: {len(chunks)}")
print(f"Total chars: {sum(c['char_count'] for c in chunks):,}")
print(f"Avg chunk size: {sum(c['char_count'] for c in chunks) // len(chunks)} chars")

# Show sample chunks
print("\n=== Sample Chunks ===")
for c in chunks[:5]:
    print(f"\n[{c['id']}] {c['title']}")
    print(f"  Section: {c['section']}")
    print(f"  Size: {c['char_count']} chars")
    print(f"  Preview: {c['text'][:100]}...")

# Save to JSON
os.makedirs(os.path.dirname(CHUNKS_OUTPUT), exist_ok=True)
with open(CHUNKS_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(chunks, f, indent=2, ensure_ascii=False)

print(f"\n✅ Chunks saved to: {CHUNKS_OUTPUT}")
