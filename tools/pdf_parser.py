"""Utilities for extracting text from PDF documents."""

from __future__ import annotations

from pathlib import Path


def parse_pdf(pdf_path: str | Path, max_chars: int = 50_000) -> str:
    """Extract text from a PDF and truncate it to ``max_chars`` characters."""
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
            text = "\n".join(page.get_text("text") for page in document)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"PDF parsing failed: {path}; reason: {exc}") from exc

    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError(f"No text could be extracted from the PDF; it may be a scanned document: {path}")
    return cleaned_text[:max_chars]
