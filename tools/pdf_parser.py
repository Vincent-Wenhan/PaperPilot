"""Utilities for extracting text from PDF documents."""

from __future__ import annotations

import re
from pathlib import Path


DEFAULT_MAX_CHARS = 120_000


def _truncate_text(text: str, max_chars: int) -> str:
    """Keep both the paper body opening and ending when truncation is required."""
    if len(text) <= max_chars:
        return text
    marker = "\n\n[... PDF text truncated by PaperPilot ...]\n\n"
    if max_chars <= len(marker):
        return text[:max_chars]
    available = max_chars - len(marker)
    head_chars = int(available * 0.75)
    return f"{text[:head_chars]}{marker}{text[-(available - head_chars):]}"


def parse_pdf(pdf_path: str | Path, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Extract page-marked PDF text within the configured context budget."""
    path = Path(pdf_path).expanduser()
    if max_chars <= 0:
        raise ValueError("max_chars must be a positive integer.")
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"File is not a PDF: {path}")

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            "Missing PDF parsing dependency PyMuPDF. Please install requirements.txt."
        ) from exc

    try:
        with fitz.open(path) as document:
            if document.needs_pass:
                raise ValueError(f"PDF is encrypted and cannot be parsed: {path}")
            text = "\n\n".join(
                f"[Page {page_number}]\n{page.get_text('text')}"
                for page_number, page in enumerate(document, 1)
            )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"PDF parsing failed: {path}; reason: {exc}") from exc

    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError(f"No text could be extracted from the PDF; it may be a scanned document: {path}")
    return _truncate_text(cleaned_text, max_chars)


def analyze_pdf_quality(pdf_path: str | Path) -> dict[str, object]:
    """Analyze PDF text quality: page count, char density, scanned detection."""
    path = Path(pdf_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Missing PyMuPDF dependency.") from exc

    with fitz.open(path) as document:
        if document.needs_pass:
            raise ValueError("PDF is encrypted.")
        num_pages = len(document)
        page_texts: list[str] = []
        for page in document:
            page_texts.append(page.get_text("text"))

    total_chars = sum(len(t) for t in page_texts)
    avg_chars = total_chars / max(num_pages, 1)
    is_scanned = avg_chars < 100

    return {
        "pdf_path": str(path),
        "filename": path.name,
        "total_chars": total_chars,
        "num_pages": num_pages,
        "avg_chars_per_page": round(avg_chars, 1),
        "is_scanned": is_scanned,
        "file_extension": path.suffix.lower(),
        "warnings": ["Very low text density; may be a scanned document. Consider OCR."] if is_scanned else [],
    }


SECTION_KEYWORDS: dict[str, tuple[str, int]] = {
    "figures": (r"(?i)\b(figure|fig\.)\s*\d+", 5),
    "tables": (r"(?i)\btable\s*\d+", 4),
    "algorithms": (r"(?i)\balgorithm\s*\d+", 4),
    "equations": (r"(?i)\beq(uation)?\.?\s*\(?\d*\)?", 3),
}


def extract_pdf_sections(
    pdf_path: str | Path,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict[str, object]:
    """Extract text from PDF with section-specific caption blocks.

    Returns main text plus lists of paragraphs matching figure, table,
    algorithm, or equation references.
    """
    path = Path(pdf_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Missing PyMuPDF dependency.") from exc

    with fitz.open(path) as document:
        if document.needs_pass:
            raise ValueError("PDF is encrypted.")
        all_text = ""
        sections: dict[str, list[str]] = {"figures": [], "tables": [], "algorithms": [], "equations": []}
        warnings: list[str] = []

        for page_num, page in enumerate(document, 1):
            blocks = page.get_text("blocks")
            for block in blocks:
                block_text = block[4].strip() if len(block) > 4 else ""
                if not block_text:
                    continue
                all_text += block_text + "\n"

                for section_name, (pattern, _) in SECTION_KEYWORDS.items():
                    if re.search(pattern, block_text):
                        snippet = block_text[:500]
                        sections[section_name].append(f"[Page {page_num}] {snippet}")

        total_chars = len(all_text)
        num_pages = len(document)
        avg_chars = total_chars / max(num_pages, 1)
        if avg_chars < 100:
            warnings.append("Very low text density; may be a scanned document. Consider OCR.")

        cleaned = _truncate_text(all_text.strip(), max_chars)
        result: dict[str, object] = {
            "main_text": cleaned if cleaned else "",
            "warnings": warnings,
        }
        for k, v in sections.items():
            result[k] = v[:20]
        return result
