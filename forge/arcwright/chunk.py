"""
Semantic chunking module.
Splits markdown text by heading structure (semantic boundaries),
not by arbitrary token count. Each chunk = one concept/section.
"""
import re
import hashlib
from . import config


def chunk_markdown(text: str, source_name: str = "") -> list:
    """
    Split markdown into semantic chunks based on heading structure.
    
    Chunking strategy:
    - H1 (#) = Book Part / Major Section — becomes `section` metadata
    - H2 (##) = Chapter — becomes chunk boundary with `title`
    - H3 (###) = Sub-chapter / Concept — becomes chunk boundary with `title`
    - Content between headings = chunk body
    
    Returns:
        List of dicts: {id, title, section, source, text, char_count}
    """
    lines = text.split("\n")
    chunks = []
    current_section = ""       # From H1
    current_chapter = ""       # From H2
    current_text = []
    
    def save_chunk():
        nonlocal current_text
        content = "\n".join(current_text).strip()
        if len(content) < config.CHUNK_MIN_CHARS:
            current_text = []
            return
        
        # Use chapter as title, section as context
        title = current_chapter or current_section or source_name
        
        # Generate stable ID from content hash
        chunk_id = hashlib.md5(content[:100].encode()).hexdigest()[:8]
        
        chunks.append({
            "id": f"{source_name[:20]}_{chunk_id}",
            "title": re.sub(r'\*\*', '', title),            # Clean bold markers
            "section": re.sub(r'\*\*', '', current_section),
            "source": source_name,
            "text": content,
            "char_count": len(content),
        })
        current_text = []
    
    for line in lines:
        heading_match = re.match(r'^(#{1,3})\s+(.+)$', line)
        
        if heading_match:
            # Save previous chunk before starting new one
            save_chunk()
            
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            
            if level == 1:
                current_section = heading_text
                current_chapter = ""
                current_text = [line]  # Keep heading as context
            elif level == 2:
                current_chapter = heading_text
                current_text = [line]
            elif level == 3:
                # H3 is a concept within a chapter — use as new chunk start
                current_text = [line]
        else:
            current_text.append(line)
    
    # Save the last chunk
    save_chunk()
    
    # Filter out oversized chunks (likely missed splits)
    chunks = [c for c in chunks if c["char_count"] <= config.CHUNK_MAX_CHARS]
    
    return chunks


def get_chunk_stats(chunks: list) -> dict:
    """Get statistics about chunks."""
    if not chunks:
        return {"count": 0, "total_chars": 0, "avg_chars": 0, "min_chars": 0, "max_chars": 0}
    
    sizes = [c["char_count"] for c in chunks]
    return {
        "count": len(chunks),
        "total_chars": sum(sizes),
        "avg_chars": sum(sizes) // len(sizes),
        "min_chars": min(sizes),
        "max_chars": max(sizes),
    }
