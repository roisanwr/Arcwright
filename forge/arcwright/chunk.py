"""
Semantic chunking module (Layer 4 — refactored).

Splits markdown by heading structure (semantic boundaries),
with configurable heading levels, size limits, and post-processing.

Supports:
- H1/H2/H3/H4 as configurable chunk boundaries
- Adaptive min/max char limits
- Post-processing: merge tiny chunks, force-split oversized
- Overlap between consecutive chunks for context continuity
"""

import re
import hashlib
from . import config


def chunk_markdown(
    text: str,
    source_name: str = "",
    heading_levels: list = None,
    min_chars: int = None,
    max_chars: int = None,
    hard_max_chars: int = None,
    overlap_chars: int = None,
    use_h4: bool = False,
) -> list:
    """
    Split markdown into semantic chunks based on heading structure.

    Chunking strategy:
    - H1 (#) = Book Part / Major Section — becomes `section` metadata
    - H2 (##) = Chapter — becomes chunk boundary with `title`
    - H3 (###) = Sub-chapter / Concept — becomes chunk boundary
    - H4 (####) = Sub-section — optional chunk boundary (when use_h4=True)

    Post-processing:
    - Chunks below `min_chars` are merged with previous chunk
    - Chunks above `hard_max_chars` are force-split by paragraph
    - Chunks between `max_chars` and `hard_max_chars` are flagged for
      semantic refinement (tagged with `refiner_needed: true`)
    - Overlap text from previous chunk is appended when `overlap_chars > 0`

    Args:
        text: Cleaned markdown text (from Layer 2)
        source_name: Name of the source file for metadata
        heading_levels: List of heading levels to treat as boundaries
                        (default: [1, 2, 3] — H1/H2/H3)
        min_chars: Minimum chars per chunk (below = merge with previous)
        max_chars: Max chars before chunk is flagged for semantic refiner
        hard_max_chars: Absolute max — force-split at this size
        overlap_chars: Number of chars from previous chunk to prepend
        use_h4: Shortcut to add H4 to heading_levels (convenience)

    Returns:
        List of chunk dicts:
            id: str — stable hash-based ID
            title: str — nearest heading title
            section: str — nearest H1 section title
            source: str — source filename
            text: str — chunk content
            char_count: int
            refiner_needed: bool — True if chunk exceeds max_chars
    """
    # ─── Apply defaults from config ──────────────────────────
    if heading_levels is None:
        heading_levels = config.CHUNK_HEADING_LEVELS
    if use_h4 and 4 not in heading_levels:
        heading_levels = sorted([*heading_levels, 4])
    if min_chars is None:
        min_chars = config.CHUNK_MIN_CHARS
    if max_chars is None:
        max_chars = config.CHUNK_MAX_CHARS
    if hard_max_chars is None:
        hard_max_chars = config.CHUNK_HARD_MAX_CHARS
    if overlap_chars is None:
        overlap_chars = config.CHUNK_OVERLAP_CHARS

    # ─── Parse heading pattern from levels ───────────────────
    # Build regex like ^#{1,3}\s+.+$  or  ^#{1,4}\s+.+$
    max_level = max(heading_levels)
    pattern = re.compile(rf'^#{{1,{max_level}}}\s+(.+)$')

    lines = text.split("\n")
    chunks = []
    current_section = ""     # From highest-level heading (typically H1)
    current_title = ""       # From nearest heading below section
    current_text = []
    current_ref_level = 0    # Heading level that started this chunk

    def heading_level(line: str) -> int:
        """Count leading '#' chars to determine heading level."""
        count = 0
        for ch in line:
            if ch == '#':
                count += 1
            else:
                break
        return count

    def save_chunk():
        """Flush accumulated text as a chunk."""
        nonlocal current_text, current_title, current_section

        content = "\n".join(current_text).strip()
        if not content:
            current_text = []
            return

        char_count = len(content)

        # Determine title and section from context
        title = current_title or current_section or source_name
        section = current_section

        # Generate stable ID from content hash
        chunk_id = hashlib.md5(content[:100].encode()).hexdigest()[:8]

        # Check if refiner is needed
        refiner_needed = char_count > max_chars and char_count <= hard_max_chars

        chunks.append({
            "id": f"{source_name[:20]}_{chunk_id}",
            "title": _clean_heading(title),
            "section": _clean_heading(section),
            "source": source_name,
            "text": content,
            "char_count": char_count,
            "refiner_needed": refiner_needed,
        })
        current_text = []

    # ─── Main loop: walk lines, split at headings ────────────
    for line in lines:
        m = pattern.match(line)
        if m:
            # New heading found — save previous chunk
            save_chunk()

            heading_text = m.group(1).strip()
            level = heading_level(line)

            # Update structural context
            if level == 1 or (current_ref_level > 0 and level <= current_ref_level):
                # H1 always resets section
                # Lower-level heading in same hierarchy also resets
                pass

            if level == 1:
                current_section = heading_text
                current_title = ""
            elif level <= max_level:
                current_title = heading_text

            current_ref_level = level
            current_text = [line]  # Keep heading as first line of chunk
        else:
            current_text.append(line)

    # Save the last chunk
    save_chunk()

    # ── Post-process: merge tiny, force-split huge ──────────
    chunks = _post_process(chunks, min_chars, max_chars, hard_max_chars, source_name)

    # ─── Add overlap ─────────────────────────────────────────
    if overlap_chars > 0:
        chunks = _add_overlap(chunks, overlap_chars)

    return chunks


# ─── Post-Processing ─────────────────────────────────────────

def _post_process(
    chunks: list,
    min_chars: int,
    max_chars: int,
    hard_max_chars: int,
    source_name: str,
) -> list:
    """
    Post-process chunks:
    1. Merge tiny chunks (< min_chars) into previous chunk
    2. Force-split oversized chunks (> hard_max_chars) by paragraph
    3. Recalculate metadata after changes
    """
    if not chunks:
        return []

    result = []

    for i, chunk in enumerate(chunks):
        # ── Tiny chunk: merge into previous (or next) ─────
        if chunk["char_count"] < min_chars:
            if result:
                # Merge into previous
                result[-1]["text"] += "\n\n" + chunk["text"]
                result[-1]["char_count"] = len(result[-1]["text"])
            elif i + 1 < len(chunks):
                # First chunk is tiny — merge into next instead
                chunks[i + 1]["text"] = chunk["text"] + "\n\n" + chunks[i + 1]["text"]
                chunks[i + 1]["char_count"] = len(chunks[i + 1]["text"])
            # else: only chunk, leave as-is
            continue

        # ── Oversized chunk: force-split ──────────────────
        if chunk["char_count"] > hard_max_chars:
            sub_chunks = _force_split(chunk, hard_max_chars, source_name)
            result.extend(sub_chunks)
            continue

        # ── Normal chunk: pass through ────────────────────
        result.append(chunk)

    # ── Recalculate refiner_needed for all chunks ─────────
    for c in result:
        c["refiner_needed"] = min_chars <= c["char_count"] <= hard_max_chars and c["char_count"] > max_chars

    return result


def _force_split(chunk: dict, hard_max: int, source_name: str) -> list:
    """
    Force-split a chunk that exceeds hard_max_chars.
    
    Strategy: split by double newline (paragraph boundary) first,
    then accumulate paragraphs into new chunks ≤ hard_max.
    """
    paragraphs = chunk["text"].split("\n\n")
    sub_chunks = []
    current_paras = []
    current_size = 0

    for para in paragraphs:
        para_size = len(para) + 2  # +2 for the "\n\n" we'll add

        if current_size + para_size > hard_max and current_paras:
            # Save current accumulation
            sub_text = "\n\n".join(current_paras)
            sub_id = hashlib.md5(sub_text[:100].encode()).hexdigest()[:8]
            sub_chunks.append({
                "id": f"{source_name[:20]}_{sub_id}",
                "title": chunk["title"],
                "section": chunk["section"],
                "source": chunk["source"],
                "text": sub_text,
                "char_count": len(sub_text),
                "refiner_needed": False,
            })
            current_paras = [para]
            current_size = para_size
        else:
            current_paras.append(para)
            current_size += para_size

    # Don't forget the last batch
    if current_paras:
        sub_text = "\n\n".join(current_paras)
        sub_id = hashlib.md5(sub_text[:100].encode()).hexdigest()[:8]
        sub_chunks.append({
            "id": f"{source_name[:20]}_{sub_id}",
            "title": chunk["title"],
            "section": chunk["section"],
            "source": chunk["source"],
            "text": sub_text,
            "char_count": len(sub_text),
            "refiner_needed": False,
        })

    return sub_chunks


def _add_overlap(chunks: list, overlap_chars: int) -> list:
    """
    Add overlap from previous chunk for context continuity.
    
    Each chunk (except first) gets:
    [last `overlap_chars` chars of previous chunk] + "\n\n" + [chunk text]
    
    The char_count is updated to reflect the total.
    """
    if len(chunks) < 2:
        return chunks

    result = [chunks[0]]

    for i in range(1, len(chunks)):
        prev_text = chunks[i - 1]["text"]
        overlap = prev_text[-overlap_chars:] if len(prev_text) > overlap_chars else prev_text

        chunk = dict(chunks[i])
        chunk["text"] = overlap + "\n\n" + chunk["text"]
        chunk["char_count"] = len(chunk["text"])
        result.append(chunk)

    return result


# ─── Helpers ─────────────────────────────────────────────────

def _clean_heading(text: str) -> str:
    """Remove markdown formatting from heading text."""
    return re.sub(r'\*\*', '', text)


def get_chunk_stats(chunks: list) -> dict:
    """Get comprehensive statistics about chunks."""
    if not chunks:
        return {
            "count": 0,
            "total_chars": 0,
            "avg_chars": 0,
            "min_chars": 0,
            "max_chars": 0,
            "refiner_needed": 0,
            "flagged_pct": 0,
        }

    sizes = [c["char_count"] for c in chunks]
    refiner_count = sum(1 for c in chunks if c.get("refiner_needed", False))

    return {
        "count": len(chunks),
        "total_chars": sum(sizes),
        "avg_chars": sum(sizes) // len(sizes),
        "min_chars": min(sizes),
        "max_chars": max(sizes),
        "refiner_needed": refiner_count,
        "flagged_pct": round(refiner_count / len(chunks) * 100, 1) if chunks else 0,
    }
