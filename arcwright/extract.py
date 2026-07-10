"""
PDF extraction module using marker-pdf.
Supports both digital and scanned (image-based) PDFs via OCR.
"""
import sys
import os
import time


def get_marker_path():
    """Find marker-pdf in the venv site-packages."""
    venv_base = os.path.expanduser("~/Arcwright/venv")
    lib = os.path.join(venv_base, "lib")
    if os.path.isdir(lib):
        for d in os.listdir(lib):
            site_pkg = os.path.join(lib, d, "site-packages")
            if os.path.isdir(site_pkg):
                return site_pkg
    return None


def extract_pdf(pdf_path: str, force_ocr: bool = True) -> str:
    """
    Extract PDF to markdown text.
    
    Args:
        pdf_path: Path to the PDF file
        force_ocr: If True, always use OCR (needed for scanned/image PDFs).
                   If False, try text extraction first, fall back to OCR.
    
    Returns:
        Full markdown text of the extracted PDF
    """
    # Add marker to path if needed
    marker_path = get_marker_path()
    if marker_path and marker_path not in sys.path:
        sys.path.insert(0, marker_path)

    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.config.parser import ConfigParser
    from marker.output import text_from_rendered

    config = {
        "output_format": "markdown",
        "force_ocr": force_ocr,
        "disable_tqdm": True,
        "use_llm": False,
    }

    config_parser = ConfigParser(config)
    converter = PdfConverter(
        config=config_parser.generate_config_dict(),
        artifact_dict=create_model_dict(),
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),
    )

    print(f"  Extracting: {os.path.basename(pdf_path)} (OCR={'ON' if force_ocr else 'AUTO'})...")
    start = time.time()
    rendered = converter(pdf_path)
    full_text, _, images = text_from_rendered(rendered)
    elapsed = time.time() - start
    
    print(f"  ✅ Done in {elapsed:.1f}s — {len(full_text):,} chars, {len(images)} images")
    return full_text
