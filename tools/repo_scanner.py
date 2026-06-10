"""Read-only repository structure scanner."""

from __future__ import annotations

from pathlib import Path
from typing import Any


IMPORTANT_NAMES = {
    "README.md",
    "README.rst",
    "README.txt",
    "requirements.txt",
    "environment.yml",
    "environment.yaml",
    "setup.py",
    "pyproject.toml",
    "train.py",
    "main.py",
    "eval.py",
    "test.py",
    "demo.py",
}
IMPORTANT_DIRECTORIES = {"scripts", "configs", "examples", "notebooks"}
ENTRYPOINT_NAMES = {"train.py", "main.py", "eval.py", "test.py", "demo.py"}
CONFIG_SUFFIXES = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"}
SKIPPED_DIRECTORIES = {".git", "__pycache__", ".venv", "venv", "node_modules"}


def _read_text(path: Path, max_chars: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError as exc:
        return f"[Unable to read {path.name}: {exc}]"


def _relative_paths(paths: list[Path], root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in paths)


def scan_repo(
    repo_path: str | Path,
    max_file_chars: int = 12_000,
) -> dict[str, Any]:
    """Scan a local repository without executing any of its contents."""
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Repository directory does not exist: {root}")
    if max_file_chars <= 0:
        raise ValueError("max_file_chars must be a positive integer.")

    files: list[Path] = []
    directories: list[Path] = []
    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        if any(part in SKIPPED_DIRECTORIES for part in relative_parts):
            continue
        if path.is_symlink():
            continue
        if path.is_dir():
            directories.append(path)
        elif path.is_file():
            files.append(path)

    important_files = [
        path for path in files if path.name in IMPORTANT_NAMES
    ]
    important_directories = [
        path for path in directories if path.name in IMPORTANT_DIRECTORIES
    ]
    entrypoints = [
        path
        for path in files
        if path.name in ENTRYPOINT_NAMES
        or (
            len(path.relative_to(root).parts) >= 2
            and path.relative_to(root).parts[0] == "examples"
            and path.name.endswith(".py")
        )
    ]
    config_files = [
        path
        for path in files
        if path.suffix.lower() in CONFIG_SUFFIXES
        or "config" in path.name.lower()
    ]

    readme = next(
        (path for path in files if path.name.lower().startswith("readme")),
        None,
    )
    requirements = next(
        (path for path in files if path.name == "requirements.txt"),
        None,
    )
    environment = next(
        (
            path
            for path in files
            if path.name in {"environment.yml", "environment.yaml"}
        ),
        None,
    )
    setup_file = next(
        (path for path in files if path.name in {"setup.py", "pyproject.toml"}),
        None,
    )

    return {
        "repo_path": str(root),
        "important_files": _relative_paths(important_files, root),
        "directories": _relative_paths(directories, root),
        "important_directories": _relative_paths(important_directories, root),
        "possible_entrypoints": _relative_paths(entrypoints, root),
        "config_files": _relative_paths(config_files, root),
        "readme_content": _read_text(readme, max_file_chars) if readme else "",
        "requirements_content": (
            _read_text(requirements, max_file_chars) if requirements else ""
        ),
        "environment_content": (
            _read_text(environment, max_file_chars) if environment else ""
        ),
        "setup_content": (
            _read_text(setup_file, max_file_chars) if setup_file else ""
        ),
    }
