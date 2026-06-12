"""Regex-based repository evidence tools."""

from __future__ import annotations

import re
from pathlib import Path

from tools.file_tools import SECRET_NAMES, SKIP_NAMES, resolve_allowed_path


def _source_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_NAMES or part.lower() in SECRET_NAMES for part in relative.parts):
            continue
        if path.suffix.lower() in {".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json"}:
            yield path


def code_search(
    root: str | Path,
    pattern: str,
    *,
    allowed_roots: list[str | Path],
    max_results: int = 100,
) -> list[dict[str, object]]:
    resolved = resolve_allowed_path(root, allowed_roots)
    regex = re.compile(pattern, re.IGNORECASE)
    results: list[dict[str, object]] = []
    for path in _source_files(resolved):
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            1,
        ):
            if regex.search(line):
                results.append(
                    {
                        "path": path.relative_to(resolved).as_posix(),
                        "line": line_number,
                        "snippet": line[:500],
                    }
                )
                if len(results) >= max_results:
                    return results
    return results


def find_entrypoints(
    root: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> list[str]:
    resolved = resolve_allowed_path(root, allowed_roots)
    candidates = {
        "main.py",
        "train.py",
        "eval.py",
        "test.py",
        "demo.py",
        "app.py",
    }
    return sorted(
        path.relative_to(resolved).as_posix()
        for path in _source_files(resolved)
        if path.name in candidates
    )


def find_dataset_paths(root: str | Path, *, allowed_roots: list[str | Path]):
    return code_search(root, r"\b(data(set)?|dataloader|data_dir)\b", allowed_roots=allowed_roots)


def find_checkpoint_keywords(root: str | Path, *, allowed_roots: list[str | Path]):
    return code_search(root, r"\b(checkpoint|ckpt|pretrained|weights)\b", allowed_roots=allowed_roots)


def find_todo_or_missing(root: str | Path, *, allowed_roots: list[str | Path]):
    return code_search(root, r"\b(TODO|FIXME|NotImplemented|missing)\b", allowed_roots=allowed_roots)
