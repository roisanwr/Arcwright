"""
Document Boundary Detection (Layer 1.5).

Identifies and tags document sections before chunking:
- [CONTENT] — Main content: chapters, sections, narrative → will be chunked & embedded
- [META]    — Front/back matter: foreword, preface, afterword, about author → stored as metadata
- [SKIP]    — Non-content: index, bibliography, copyright, blank pages → excluded entirely

Two modes:
1. LLM-powered (when USE_LLM=True) — precise detection using content analysis
2. Heuristic fallback — keyword-based heading matching
"""

import re
from . import config
from .utils import llm


# ─── Known Section Keywords ─────────────────────────────

CONTENT_KEYWORDS = [
    "chapter", "chapter ", "part ", "section", "act ", "scene",
    "prologue", "epilogue", "introduction",
]

META_KEYWORDS = [
    "foreword", "preface", "afterword", "acknowledgments", "acknowledgements",
    "about the author", "about the editor", "author's note", "editor's note",
    "a note from", "introduction by", "preface to", "publisher's note",
    "dedication", "epigraph", "a note to the reader",
]

SKIP_KEYWORDS = [
    "index", "bibliography", "references", "works cited", "further reading",
    "copyright", "also by", "credits", "colophon", "illustration credits",
    "photo credits", "permissions", "license", "glossary", "appendix",
    "appendices", "about the publisher", "notes", "endnotes",
]


# ─── Main Entry Point ─────────────────────────────────

def detect_sections(text: str, source_name: str = "") -> list:
    """
    Detect and tag sections in document.
    
    Returns list of dicts:
        {tag: "CONTENT"|"META"|"SKIP", label: str, line_start: int, line_end: int}
    
    Uses LLM when available, falls back to heading keyword matching.
    """
    if config.USE_LLM:
        result = _detect_with_llm(text, source_name)
        if result:
            return result
    
    return _detect_with_heuristic(text)


def apply_boundaries(text: str, sections: list) -> str:
    """
    Apply section tags to text by prepending markers.
    Chunker can then parse these markers.
    
    Returns text with boundary markers:
        <!-- BOUNDARY:CONTENT -->
        <!-- BOUNDARY:META:Foreword by X -->
        <!-- BOUNDARY:SKIP -->
    """
    lines = text.split('\n')
    tagged_lines = []
    
    # Sort sections by line_start
    sorted_sections = sorted(sections, key=lambda s: s['line_start'])
    
    current_tag = "CONTENT"
    section_idx = 0
    
    for i, line in enumerate(lines):
        # Check if we're entering a new section
        while section_idx < len(sorted_sections) and sorted_sections[section_idx]['line_start'] <= i:
            sec = sorted_sections[section_idx]
            label = sec.get('label', '')
            if sec['tag'] == 'META':
                tagged_lines.append(f"<!-- BOUNDARY:META:{label} -->")
            else:
                tagged_lines.append(f"<!-- BOUNDARY:{sec['tag']} -->")
            current_tag = sec['tag']
            section_idx += 1
        
        # Only include CONTENT and META lines (not SKIP)
        if current_tag != 'SKIP':
            tagged_lines.append(line)
    
    return '\n'.join(tagged_lines)


def filter_chunks_by_boundary(chunks: list, sections: list) -> list:
    """
    Post-chunking filter: remove chunks from SKIP sections,
    tag chunks from META sections.
    """
    # Build line ranges for each tag type
    content_ranges = []
    meta_ranges = []
    
    for sec in sections:
        r = range(sec['line_start'], sec['line_end'] + 1)
        if sec['tag'] == 'CONTENT':
            content_ranges.append(r)
        elif sec['tag'] == 'META':
            meta_ranges.append(r)
    
    def in_ranges(chunk_text: str, ranges: list) -> bool:
        """Check if first line of chunk falls in any range."""
        first_line = chunk_text[:chunk_text.find('\n')] if '\n' in chunk_text else chunk_text
        return any(r for r in ranges)
    
    result = []
    for c in chunks:
        # Estimate which section this chunk belongs to (check first heading)
        text = c.get('text', '')
        first_heading = ''
        for line in text.split('\n'):
            if line.startswith('#'):
                first_heading = line
                break
        
        # Check if this is from CONTENT section (heuristic: chapters)
        is_content = any(kw in first_heading.lower() for kw in CONTENT_KEYWORDS if kw)
        is_meta = any(kw in first_heading.lower() for kw in META_KEYWORDS if kw)
        is_skip = any(kw in first_heading.lower() for kw in SKIP_KEYWORDS if kw)
        
        if is_skip:
            continue  # drop SKIP chunks
        elif is_meta:
            c['_section_tag'] = 'META'
        else:
            c['_section_tag'] = 'CONTENT'
        
        result.append(c)
    
    return result


# ─── LLM Detection ─────────────────────────────────────

BOUNDARY_SYSTEM = """You are a document structure analyst. Identify sections of a book/document and classify them.

Rules:
- CONTENT: Main narrative, chapters, parts, prologue, epilogue, acts, scenes
- META: Foreword, preface, introduction by OTHER person, afterword, acknowledgments, 
        dedication, about the author, author's note
- SKIP: Index, bibliography, references, appendix, copyright page, blank pages,
        endnotes, glossary, permissions, credits

Output format: JSON array of objects, no markdown, no explanation."""

BOUNDARY_PROMPT = """Analyze this document's structure from its headings and first/last content.

HEADINGS (first 60):
{headings}

FIRST 1000 CHARS:
{preview}

LAST 800 CHARS:
{tail}

For each distinct section identified, output one object with:
- label: The section title
- tag: "CONTENT" | "META" | "SKIP"
- approx_line: Approximate line number where section starts (0-indexed)

[
    {{"label": "Foreword by Stephen King", "tag": "META", "approx_line": 0}},
    {{"label": "Chapter 1: The Beginning", "tag": "CONTENT", "approx_line": 45}},
    {{"label": "Appendix: Timeline", "tag": "SKIP", "approx_line": 800}},
]
"""


def _detect_with_llm(text: str, source_name: str = "") -> list:
    """Use LLM to detect document sections."""
    lines = text.split('\n')
    
    # Extract headings for analysis
    heading_lines = []
    for i, line in enumerate(lines[:200]):
        if re.match(r'^#{1,4}\s', line):
            heading_lines.append(f"L{i}: {line}")
    
    headings = '\n'.join(heading_lines[:60])
    preview = text[:1000]
    tail = text[-800:]
    
    prompt = BOUNDARY_PROMPT.format(
        headings=headings or "(no headings found)",
        preview=preview,
        tail=tail,
    )
    
    result = llm.llm_complete(prompt, system=BOUNDARY_SYSTEM)
    if not result:
        return []
    
    # Strip markdown fences
    result = result.strip()
    if result.startswith('```'):
        result = re.sub(r'^```(?:json)?\s*', '', result)
        result = re.sub(r'\s*```$', '', result)
    
    import json as _json
    try:
        sections = _json.loads(result)
        # Validate
        for s in sections:
            s['tag'] = s.get('tag', 'CONTENT').upper()
            if s['tag'] not in ('CONTENT', 'META', 'SKIP'):
                s['tag'] = 'CONTENT'
        return sections
    except (_json.JSONDecodeError, KeyError):
        return []


# ─── Heuristic Detection ───────────────────────────────

def _detect_with_heuristic(text: str) -> list:
    """
    Heuristic section detection using heading keywords.
    
    Scans headings and classifies them based on known keywords.
    Falls back to treating everything as CONTENT when uncertain.
    """
    lines = text.split('\n')
    sections = []
    current_section = None
    
    for i, line in enumerate(lines):
        m = re.match(r'^(#{1,4})\s+(.+)$', line)
        if not m:
            continue
        
        heading = m.group(2).strip().lower()
        
        # Detect tag from keywords
        if _matches_any(heading, SKIP_KEYWORDS):
            tag, label = 'SKIP', m.group(2).strip()
        elif _matches_any(heading, META_KEYWORDS):
            tag, label = 'META', m.group(2).strip()
        else:
            tag, label = 'CONTENT', m.group(2).strip()
        
        # Close previous section
        if current_section:
            current_section['line_end'] = i - 1
        
        current_section = {
            'label': label,
            'tag': tag,
            'line_start': i,
            'line_end': len(lines) - 1,
        }
        sections.append(current_section)
    
    # Close last section
    if current_section:
        current_section['line_end'] = len(lines) - 1
    
    # If no sections found, treat everything as CONTENT
    if not sections:
        sections = [{'label': 'Document', 'tag': 'CONTENT', 'line_start': 0, 'line_end': len(lines) - 1}]
    
    return sections


def _matches_any(text: str, keywords: list) -> bool:
    """Check if text contains any of the keywords."""
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower:
            return True
    return False


# ─── Stats ─────────────────────────────────────────────

def get_boundary_stats(sections: list) -> dict:
    """Get statistics about detected boundaries."""
    return {
        "total_sections": len(sections),
        "content": sum(1 for s in sections if s['tag'] == 'CONTENT'),
        "meta": sum(1 for s in sections if s['tag'] == 'META'),
        "skip": sum(1 for s in sections if s['tag'] == 'SKIP'),
        "labels": [s['label'] for s in sections],
    }
