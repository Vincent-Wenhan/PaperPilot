"""Optional OCR fallback for scanned or low-text PDFs."""

from __future__ import annotations

from pathlib import Path


class OcrUnavailableError(RuntimeError):
    """Raised when OCR dependencies or binaries are missing."""


def ocr_available() -> bool:
    """Return whether OCR dependencies are importable."""
    try:
        import fitz  # noqa: F401
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return True


def ocr_pdf_text(
    pdf_path: str | Path,
    *,
    max_pages: int = 20,
    dpi: int = 200,
) -> str:
    """Render PDF pages to images and extract text with Tesseract OCR."""
    if not ocr_available():
        raise OcrUnavailableError(
            "OCR dependencies are not installed. Install pytesseract and a "
            "system Tesseract binary, or provide a text-based PDF."
        )

    import io

    import fitz
    import pytesseract
    from PIL import Image

    path = Path(pdf_path).expanduser()
    page_texts: list[str] = []
    with fitz.open(path) as document:
        for page_number, page in enumerate(document, 1):
            if page_number > max_pages:
                break
            pixmap = page.get_pixmap(dpi=dpi)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            text = pytesseract.image_to_string(image)
            cleaned = text.strip()
            if cleaned:
                page_texts.append(f"[Page {page_number}]\n{cleaned}")
    return "\n\n".join(page_texts)
