"""Validation and shallow cloning helpers for public GitHub repositories."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse


_REPO_PART_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def _parse_github_repo(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.hostname not in {"github.com", "www.github.com"}:
        return None
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None

    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        return None
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        return None
    if not _REPO_PART_PATTERN.fullmatch(owner):
        return None
    if not _REPO_PART_PATTERN.fullmatch(repo):
        return None
    return owner, repo


def is_valid_github_url(url: str) -> bool:
    """Return whether ``url`` identifies a GitHub owner/repository pair."""
    return _parse_github_repo(url) is not None


def clone_github_repo(
    github_url: str,
    workspace_dir: str | Path = "workspace",
) -> Path:
    """Clone a GitHub repository with depth one and return its local path."""
    repo_parts = _parse_github_repo(github_url)
    if repo_parts is None:
        raise ValueError(
            "Invalid GitHub URL. Only https://github.com/owner/repo is supported."
        )

    owner, repo = repo_parts
    workspace = Path(workspace_dir).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    repo_path = workspace / f"{owner}__{repo}"

    if repo_path.exists():
        if (repo_path / ".git").is_dir():
            return repo_path
        raise FileExistsError(f"Target directory exists but is not a Git repository: {repo_path}")

    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", github_url, str(repo_path)],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("GitHub clone timed out. This may be a network issue.") from exc
    except OSError as exc:
        raise RuntimeError(f"Unable to start git clone: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"GitHub clone failed. This may be a network, permission, or repository address issue: {detail}"
        )
    return repo_path
