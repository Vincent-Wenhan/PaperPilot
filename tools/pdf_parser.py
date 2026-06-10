"""Utilities for extracting text from PDF documents."""

from __future__ import annotations

from pathlib import Path


def parse_pdf(pdf_path: str | Path, max_chars: int = 50_000) -> str:
    """Extract text from a PDF and truncate it to ``max_chars`` characters."""
    path = Path(pdf_path).expanduser()
    if max_chars <= 0:
        raise ValueError("max_chars 必须是正整数。")
    if not path.is_file():
        raise FileNotFoundError(f"PDF 文件不存在：{path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"文件不是 PDF：{path}")

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            "缺少 PDF 解析依赖 PyMuPDF，请先安装 requirements.txt。"
        ) from exc

    try:
        with fitz.open(path) as document:
            if document.needs_pass:
                raise ValueError(f"PDF 已加密，无法解析：{path}")
            text = "\n".join(page.get_text("text") for page in document)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"PDF 解析失败：{path}；原因：{exc}") from exc

    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError(f"PDF 未提取到文本，文件可能是扫描版：{path}")
    return cleaned_text[:max_chars]
