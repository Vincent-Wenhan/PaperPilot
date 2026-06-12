"""Read-only filesystem tools with explicit project-root restrictions."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

SECRET_NAMES = {
    ".env",
    ".env.local",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
}
SKIP_NAMES = {".git", "__pycache__", ".venv", "venv", "node_modules"}


def resolve_allowed_path(
    path: str | Path,
    allowed_roots: Iterable[str | Path],
    *,
    allow_missing: bool = False,
) -> Path:
    resolved = Path(path).expanduser().resolve()
    roots = [Path(root).expanduser().resolve() for root in allowed_roots]
    if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
        raise PermissionError(f"Path is outside allowed roots: {resolved}")
    if resolved.name.lower() in SECRET_NAMES:
        raise PermissionError(f"Secret file access is prohibited: {resolved.name}")
    if not allow_missing and not resolved.exists():
        raise FileNotFoundError(resolved)
    return resolved


def read_file(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
    max_chars: int = 50_000,
) -> dict[str, object]:
    resolved = resolve_allowed_path(path, allowed_roots)
    if not resolved.is_file():
        raise ValueError(f"Not a file: {resolved}")
    text = resolved.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        raise ValueError(
            f"File exceeds the {max_chars} character limit: {resolved}"
        )
    return {
        "path": str(resolved),
        "content": text,
        "truncated": False,
    }


def read_many_files(
    paths: list[str | Path],
    *,
    allowed_roots: list[str | Path],
    max_chars: int = 50_000,
) -> list[dict[str, object]]:
    return [
        read_file(path, allowed_roots=allowed_roots, max_chars=max_chars)
        for path in paths
    ]


def list_dir(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> list[str]:
    resolved = resolve_allowed_path(path, allowed_roots)
    if not resolved.is_dir():
        raise ValueError(f"Not a directory: {resolved}")
    return sorted(
        item.name
        for item in resolved.iterdir()
        if item.name not in SKIP_NAMES and item.name.lower() not in SECRET_NAMES
    )


def tree_view(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
    max_depth: int = 3,
) -> dict[str, object]:
    root = resolve_allowed_path(path, allowed_roots)
    entries: list[str] = []
    for item in sorted(root.rglob("*")):
        relative = item.relative_to(root)
        if len(relative.parts) > max_depth:
            continue
        if any(part in SKIP_NAMES or part.lower() in SECRET_NAMES for part in relative.parts):
            continue
        entries.append(relative.as_posix() + ("/" if item.is_dir() else ""))
    return {"root": str(root), "entries": entries}
