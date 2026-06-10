"""Load approved project-local guidelines for high-level agents."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from config import GUIDELINES_DIR


def _resolve_guideline(name: str) -> Path:
    if not name or Path(name).name != name or Path(name).suffix.lower() != ".md":
        raise ValueError("Guideline name must be one Markdown filename.")
    path = (GUIDELINES_DIR / name).resolve()
    if path.parent != GUIDELINES_DIR.resolve():
        raise ValueError("Guideline path must stay inside guidelines/.")
    return path


def load_guideline(name: str) -> str:
    """Return one approved UTF-8 guideline by filename."""
    path = _resolve_guideline(name)
    if not path.is_file():
        raise FileNotFoundError(f"Guideline not found: {path}")
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Guideline is empty: {path}")
    return content


def load_guidelines(names: Iterable[str]) -> str:
    """Return multiple named guidelines as one prompt section."""
    sections = [load_guideline(name) for name in names]
    return "\n\n---\n\n".join(sections)
