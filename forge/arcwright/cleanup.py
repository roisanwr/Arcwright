"""
Markdown cleanup layer (Layer 2).

Pre-filters extracted markdown before chunking:
- Strips XML artifacts, empty headings, image references
- Normalizes whitespace and formatting
- Prepares clean text for accurate chunking
"""

import re
from . import config


def clean_markdown(text: str, deep: bool = False) -> str:
    """
    Clean extracted markdown text by removing artifacts.
    
    Two-pass approach:
    1. Regex pre-clean (always runs — fast, deterministic)
    2. Optional LLM deep-clean (when deep=True and USE_LLM=True)
    
    Args:
        text: Raw extracted markdown from Layer 1
        deep: Whether to run LLM-based deep cleaning
    
    Returns:
        Cleaned markdown text
    """
    text = _pre_clean_regex(text)
    
    if deep and config.USE_LLM:
        text = _deep_clean_llm(text)
    
    return text


def _pre_clean_regex(text: str) -> str:
    """
    Fast regex-based cleaning. No external dependencies.
    
    Removes:
    - XML declarations: <?xml version='1.0' encoding='utf-8'?>
    - XML without <? prefix: xml version='1.0' encoding='utf-8'?
    - DOCTYPE declarations
    - CDATA sections
    - Empty heading markers: "### " / "## " / "# " with no text
    - Image references: ![alt](path)
    - Horizontal rules: "---" or "***" (3+)
    - Publisher boilerplate markers: [image], [table], etc.
    - Footnote/endnote links: [1], [2,3], [1-3]
    - Excessive blank lines (3+ → 2)
    - Leading/trailing whitespace on each line
    """
    # 1. XML declarations — with or without <?xml prefix
    text = re.sub(r'<\?xml[^>]*\?>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^xml\s+version=["\'][^"\']*["\'].*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'<!DOCTYPE[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<!\[CDATA\[.*?\]\]>', '', text, flags=re.DOTALL)
    
    # 2. Empty heading markers
    text = re.sub(r'^#{1,4}[ \t]*$', '', text, flags=re.MULTILINE)
    
    # 3. Image references
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    
    # 4. Horizontal rules
    text = re.sub(r'^(-|\*){3,}\s*$', '', text, flags=re.MULTILINE)
    
    # 5. Publisher markers
    text = re.sub(r'\[\s*(image|picture|figure|table)\s*\]', '', text, flags=re.IGNORECASE)
    
    # 6. Footnote/endnote links
    text = re.sub(r'\[\d+([,\-]\d+)*\]', '', text)
    
    # 7. Trim trailing whitespace on every line
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    
    # 8. Collapse excessive blank lines (3+ → 2)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    
    # 9. Strip leading/trailing whitespace from whole document
    text = text.strip()
    
    return text


def _deep_clean_llm(text: str) -> str:
    """
    LLM-based deep cleaning for stubborn OCR artifacts.
    
    Uses configured LLM API to:
    - Fix merged words: "T H E" → "THE"
    - Fix broken sentences split across lines incorrectly
    - Remove page numbers embedded in text: "[page 45]" or "|| 45 ||"
    - Detect and remove repeated header/footer text
    - Preserve all actual content
    
    NOTE: This is a placeholder for Phase 3 implementation.
    For now, returns regex-cleaned text as-is.
    """
    # TODO: Implement LLM call when USE_LLM=True (Phase 3)
    return text


def get_cleanup_stats(original: str, cleaned: str) -> dict:
    """Get statistics about the cleaning process."""
    return {
        "original_chars": len(original),
        "cleaned_chars": len(cleaned),
        "removed_chars": len(original) - len(cleaned),
        "removed_pct": round((1 - len(cleaned) / max(len(original), 1)) * 100, 1),
        "original_lines": original.count("\n") + 1,
        "cleaned_lines": cleaned.count("\n") + 1,
    }
