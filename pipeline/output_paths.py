"""Resolve reproduce-mode output file locations."""

from __future__ import annotations

from pathlib import Path

from config import OUTPUTS_DIR

OUTPUT_FILENAMES = (
    "reproduction_plan.md",
    "run.sh",
    "report.md",
)


def resolve_output_dir(result: dict[str, object] | None) -> Path:
    """Return the directory where reproduce outputs were written."""
    paper_name = str((result or {}).get("paper_name") or "").strip()
    if paper_name:
        return OUTPUTS_DIR / paper_name
    return OUTPUTS_DIR


def resolve_output_file(result: dict[str, object] | None, filename: str) -> Path:
    """Return the path to one reproduce output file."""
    return resolve_output_dir(result) / filename
