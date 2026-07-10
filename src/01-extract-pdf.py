#!/usr/bin/env python3
"""Extract full PDF to markdown using marker-pdf library."""
import sys
import os
import time

# Add marker to path
sys.path.insert(0, os.path.expanduser("~/rag-storytelling/lib/python3.12/site-packages"))

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser
from marker.output import text_from_rendered

PDF_PATH = os.path.expanduser(
    "/home/rois/Obsidian/MyVault/Efforts/Active/Story Telling automation multi agent/Books/Robert McKee - Story (pdf).pdf"
)
OUTPUT_DIR = os.path.expanduser("~/rag-storytelling-output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"[{time.strftime('%H:%M:%S')}] Loading models...", flush=True)

config = {
    "output_format": "markdown",
    "force_ocr": True,
    "disable_tqdm": True,
    "use_llm": False,
}

config_parser = ConfigParser(config)

# Create converter
converter = PdfConverter(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    processor_list=config_parser.get_processors(),
    renderer=config_parser.get_renderer(),
)

print(f"[{time.strftime('%H:%M:%S')}] Starting full PDF extraction (427 pages)...", flush=True)
start = time.time()

rendered = converter(PDF_PATH)

full_text, _, images = text_from_rendered(rendered)
elapsed = time.time() - start

# Save output
base_name = "Robert McKee - Story (pdf)"
md_path = os.path.join(OUTPUT_DIR, f"{base_name}.md")
with open(md_path, "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"[{time.strftime('%H:%M:%S')}] Done! {elapsed:.1f} seconds", flush=True)
print(f"Output: {md_path}", flush=True)
print(f"Size: {len(full_text):,} chars", flush=True)
