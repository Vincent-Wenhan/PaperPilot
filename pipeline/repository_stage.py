"""Deterministic repository acquisition and static scanning stage."""

from __future__ import annotations

from typing import Any, Callable

from config import WORKSPACE_DIR
from tools.github_tool import clone_github_repo, is_valid_github_url
from tools.repo_scanner import scan_repo_detailed


def do_clone(result: dict[str, Any], github_url: str) -> str:
    """Clone a validated public GitHub repository with deterministic tooling."""
    if not is_valid_github_url(github_url):
        result["errors"].append(
            "[GitHub URL validation failed] Only https://github.com/owner/repo format is supported."
        )
        return ""
    try:
        repo_path = clone_github_repo(github_url, WORKSPACE_DIR)
    except Exception as exc:
        result["errors"].append(f"[Repo Cloner] {exc}")
        return ""
    result["repo_path"] = str(repo_path)
    result["repo_source"] = "GitHub repository"
    return str(repo_path)


def prepare_repository(
    result: dict[str, Any],
    github_url: str,
    llm_client: Any | None = None,
    code_context: dict[str, Any] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any] | None:
    """Clone and scan a repository, or explicitly continue paper-only.

    ``llm_client`` and ``code_context`` remain accepted for compatibility but
    are intentionally unused. Repository acquisition is deterministic.
    """
    del llm_client, code_context
    if not github_url.strip():
        result["repo_source"] = "Paper only"
        return None
    if progress_callback:
        progress_callback("Repository Cloner acquiring repository")
    repo_path = do_clone(result, github_url.strip())
    if not repo_path:
        return None
    result["repo_source"] = "GitHub repository"
    try:
        repo_scan = scan_repo_detailed(repo_path)
    except Exception as exc:
        result["errors"].append(f"[Repo Scanner] {exc}")
        return None
    repo_scan["repository_source"] = result["repo_source"]
    return repo_scan
