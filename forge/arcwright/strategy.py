"""
Strategy Analyzer (Layer 3) — determines optimal chunking strategy per book.

Uses LLM (when available) for intelligent strategy selection, with
heuristic offline fallback when LLM is not configured.

Two modes:
1. analyze_llm()    — LLM-powered: analyzes structure + recommends strategy
2. analyze_offline() — Heuristic: uses heading density + content patterns
"""

import json
import re
import time
from . import config
from .utils import llm


# ─── Main Entry Point ─────────────────────────────────────

def detect_and_configure(text: str, source_name: str = "") -> dict:
    """
    Analyze text and return optimal chunking configuration.
    
    Tries LLM first (if USE_LLM=True), falls back to offline heuristic.
    
    Returns:
        dict with keys:
            strategy: "heading_based" | "hybrid" | "recursive"
            use_h4: bool
            chunk_size_min: int
            chunk_size_max: int
            heading_levels: list[int]
            notes: list[str]
    """
    # Always compute structure
    structure = _extract_structure(text)
    
    if config.USE_LLM:
        result = analyze_llm(text, structure, source_name)
        if result:
            return result
    
    return analyze_offline(structure)


# ─── LLM Analyzer ──────────────────────────────────────────

ANALYZER_SYSTEM = """You are an expert document structure analyst.
Your task is to analyze a book/document and recommend the optimal chunking strategy.
Output JSON ONLY — no markdown, no explanation, no code fences."""

ANALYZER_PROMPT = """Analyze this document and recommend chunking settings.

STRUCTURE DATA:
- Total characters: {total_chars}
- Total lines: {total_lines}
- Headings: H1={h1}, H2={h2}, H3={h3}, H4={h4}
- Empty heading markers: {empty_headings}
- XML/OCR artifacts: {xml_artifacts}
- Heading density: {heading_density:.4f} (headings per 100 lines)

FIRST 800 CHARS:
{preview}

LAST 500 CHARS:
{tail}

HEADING LIST (first 40):
{heading_list}

TASK:
1. Identify book type: "narration" | "technical" | "reference" | "mixed"
2. Recommend chunking strategy: "heading_based" | "hybrid" | "recursive"
3. Should H4 be treated as chunk boundary? (true/false)
4. Optimal min/max chars for this book
5. List any special sections to flag (foreword, appendix, index, etc.)

Output JSON only:
{{
    "book_type": "narration",
    "strategy": "hybrid",
    "use_h4": false,
    "chunk_size_min": 150,
    "chunk_size_max": 2500,
    "special_sections": ["foreword by X", "appendix A"],
    "notes": "Well-structured narrative book. H1/H2/H3 sufficient."
}}
"""


def analyze_llm(text: str, structure: dict, source_name: str = "") -> dict:
    """Analyze document via LLM and return strategy config."""
    preview = text[:800]
    tail = text[-500:]
    
    # Build heading list
    heading_lines = []
    for line in text.split('\n'):
        m = re.match(r'^(#{1,4})\s+(.+)', line)
        if m:
            heading_lines.append(f"{m.group(1)} {m.group(2)[:80]}")
    
    heading_list = '\n'.join(heading_lines[:40])
    
    prompt = ANALYZER_PROMPT.format(
        total_chars=len(text),
        total_lines=text.count('\n') + 1,
        h1=structure['h1'], h2=structure['h2'],
        h3=structure['h3'], h4=structure['h4'],
        empty_headings=structure['empty_headings'],
        xml_artifacts=structure['xml_artifacts'],
        heading_density=structure['heading_density'] * 100,
        preview=preview,
        tail=tail,
        heading_list=heading_list,
    )
    
    result = llm.llm_complete(prompt, system=ANALYZER_SYSTEM)
    if not result:
        return {}
    
    # Parse JSON from response (strip markdown fences if present)
    result = result.strip()
    if result.startswith('```'):
        result = re.sub(r'^```(?:json)?\s*', '', result)
        result = re.sub(r'\s*```$', '', result)
    
    try:
        parsed = json.loads(result)
        return {
            "strategy": parsed.get("strategy", "heading_based"),
            "use_h4": parsed.get("use_h4", False),
            "chunk_size_min": parsed.get("chunk_size_min", config.CHUNK_MIN_CHARS),
            "chunk_size_max": parsed.get("chunk_size_max", config.CHUNK_MAX_CHARS),
            "heading_levels": [4] if parsed.get("use_h4", False) else [1, 2, 3],
            "notes": [parsed.get("notes", "")] if parsed.get("notes") else [],
            "special_sections": parsed.get("special_sections", []),
            "book_type": parsed.get("book_type", "unknown"),
            "_source": "llm",
        }
    except (json.JSONDecodeError, KeyError):
        print(f"  ⚠️  LLM returned unparseable JSON, falling back to offline")
        return {}


# ─── Offline Heuristic Analyzer ────────────────────────────

def analyze_offline(structure: dict = None, text: str = None) -> dict:
    """
    Heuristic-based strategy selection. No LLM needed.
    
    Rules:
    - heading_density > 0.03 → heading_based
    - heading_density 0.01–0.03 → hybrid (heading + semantic fallback)
    - heading_density < 0.01 and > 0 → hybrid
    - heading_density = 0 → recursive
    - H4 > 30% of total headings → use_h4=True
    """
    if structure is None and text is not None:
        structure = _extract_structure(text)
    elif structure is None:
        return {
            "strategy": "recursive",
            "use_h4": False,
            "heading_levels": [1, 2, 3],
            "chunk_size_min": config.CHUNK_MIN_CHARS,
            "chunk_size_max": config.CHUNK_MAX_CHARS,
            "notes": ["No content to analyze"],
            "book_type": "unknown",
            "_source": "offline",
        }
    
    s = structure
    total_h = s['h1'] + s['h2'] + s['h3'] + s['h4']
    h4_ratio = s['h4'] / max(total_h, 1)
    
    # Strategy selection
    if s['heading_density'] > 0.03:
        strategy = "heading_based"
    elif s['heading_density'] > 0.01:
        strategy = "hybrid"
    elif total_h > 0:
        strategy = "hybrid"
    else:
        strategy = "recursive"
    
    # H4 decision
    use_h4 = h4_ratio > 0.3
    
    # Heading levels
    heading_levels = [4] if use_h4 else [1, 2, 3]
    
    # Notes
    notes = []
    if s['xml_artifacts'] > 0:
        notes.append(f"{s['xml_artifacts']} XML artifacts cleaned")
    if s['empty_headings'] > 0:
        notes.append(f"{s['empty_headings']} empty headings cleaned")
    if use_h4:
        notes.append(f"H4 ratio {h4_ratio:.0%} — enabled H4 boundaries")
    
    return {
        "strategy": strategy,
        "use_h4": use_h4,
        "heading_levels": heading_levels,
        "chunk_size_min": config.CHUNK_MIN_CHARS,
        "chunk_size_max": config.CHUNK_MAX_CHARS,
        "notes": notes,
        "book_type": "unknown",
        "_source": "offline",
    }


# ─── Structure Extraction ─────────────────────────────────

def _extract_structure(text: str) -> dict:
    """Extract structural metrics from markdown text."""
    lines = text.split('\n')
    
    h1 = len(re.findall(r'^# ', text, re.MULTILINE))
    h2 = len(re.findall(r'^## ', text, re.MULTILINE))
    h3 = len(re.findall(r'^### ', text, re.MULTILINE))
    h4 = len(re.findall(r'^#### ', text, re.MULTILINE))
    empty = len(re.findall(r'^#{1,4}\s*$', text, re.MULTILINE))
    xml = text.count('<?xml')
    
    return {
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "h4": h4,
        "empty_headings": empty,
        "xml_artifacts": xml,
        "heading_density": (h1 + h2 + h3 + h4) / max(len(lines), 1),
        "total_lines": len(lines),
        "total_chars": len(text),
    }


# ─── Report ───────────────────────────────────────────────

def format_report(config_dict: dict) -> str:
    """Format strategy config as a readable report."""
    source = config_dict.get('_source', 'unknown')
    strategy = config_dict['strategy']
    use_h4 = config_dict.get('use_h4', False)
    size_min = config_dict['chunk_size_min']
    size_max = config_dict['chunk_size_max']
    levels = config_dict['heading_levels']
    notes = config_dict.get('notes', [])
    book_type = config_dict.get('book_type', 'unknown')
    
    lines = [
        f"  📋 Strategy: {strategy} ({book_type})",
        f"     Heading levels: H{','.join(str(l) for l in levels)}",
        f"     H4 boundary: {'✅ YES' if use_h4 else '❌ NO'}",
        f"     Chunk size: {size_min}–{size_max} chars",
        f"     Source: {source}",
    ]
    if notes:
        for n in notes[:3]:
            lines.append(f"     📝 {n}")
    if config_dict.get('special_sections'):
        for s in config_dict['special_sections'][:3]:
            lines.append(f"     🏷️  Special: {s}")
    
    return '\n'.join(lines)
