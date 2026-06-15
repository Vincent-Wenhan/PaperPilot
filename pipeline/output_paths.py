"""Resolve reproduce-mode output file locations."""

from __future__ import annotations

from pathlib import Path

from config import OUTPUTS_DIR

OUTPUT_FILENAMES = (
    "reproduction_plan.md",
    "run.sh",
    "report.md",
)


def safe_output_name(raw_name: object) -> str:
    """Return a filesystem-safe single directory name for one paper output."""
    raw = str(raw_name or "").strip()
    if not raw:
        return ""

    characters: list[str] = []
    previous_was_separator = False
    for character in raw:
        if character.isalnum() or character in {"-", "_"}:
            characters.append(character)
            previous_was_separator = False
        elif not previous_was_separator:
            characters.append("_")
            previous_was_separator = True

    return "".join(characters).strip("_-")[:80]


def resolve_output_dir(result: dict[str, object] | None) -> Path:
    """Return the directory where reproduce outputs were written."""
    paper_name = safe_output_name((result or {}).get("paper_name"))
    if paper_name:
        return OUTPUTS_DIR / paper_name
    return OUTPUTS_DIR


def resolve_output_file(result: dict[str, object] | None, filename: str) -> Path:
    """Return the path to one reproduce output file."""
    if filename not in OUTPUT_FILENAMES:
        raise ValueError(f"Unknown output filename: {filename}")
    return resolve_output_dir(result) / filename
