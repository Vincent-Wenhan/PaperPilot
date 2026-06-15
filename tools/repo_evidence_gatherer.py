"""Gather deterministic repository evidence via the tool registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.tool_executor import ToolExecutor
from runtime.tool_registry import build_default_registry
from schemas.tool_schema import ToolCall

AGENT_NAME = "Repository Understanding Agent"
README_CANDIDATES = (
    "README.md",
    "README.rst",
    "README",
    "readme.md",
)
DEPENDENCY_CANDIDATES = (
    "requirements.txt",
    "environment.yml",
    "pyproject.toml",
    "setup.py",
)


def gather_repo_evidence(repo_path: str | Path) -> dict[str, Any]:
    """Read key repository files and search signals using registered tools."""
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        return {"repo_path": str(root), "available": False, "notes": ["Repository path is missing."]}

    registry = build_default_registry()
    executor = ToolExecutor(registry)
    allowed_roots = [str(root)]
    evidence: dict[str, Any] = {
        "repo_path": str(root),
        "available": True,
        "readme_excerpt": "",
        "dependency_summaries": [],
        "entrypoints": [],
        "todo_markers": [],
        "notes": [],
    }

    for readme_name in README_CANDIDATES:
        readme_path = root / readme_name
        if not readme_path.is_file():
            continue
        result = executor.run(
            ToolCall(
                tool_name="read_file",
                arguments={"path": str(readme_path), "allowed_roots": allowed_roots},
                requested_by=AGENT_NAME,
            )
        )
        if result.success and isinstance(result.output, dict):
            content = str(result.output.get("content") or "")
            evidence["readme_excerpt"] = content[:4000]
            evidence["notes"].append(f"Read {readme_name} via read_file tool.")
            break

    for dep_name in DEPENDENCY_CANDIDATES:
        dep_path = root / dep_name
        if not dep_path.is_file():
            continue
        result = executor.run(
            ToolCall(
                tool_name="parse_dependency_file",
                arguments={"path": str(dep_path), "allowed_roots": allowed_roots},
                requested_by=AGENT_NAME,
            )
        )
        if result.success:
            evidence["dependency_summaries"].append(
                {"file": dep_name, "summary": result.output}
            )

    for tool_name, key in (
        ("find_entrypoints", "entrypoints"),
        ("find_todo_or_missing", "todo_markers"),
    ):
        result = executor.run(
            ToolCall(
                tool_name=tool_name,
                arguments={"root": str(root), "allowed_roots": allowed_roots},
                requested_by=AGENT_NAME,
            )
        )
        if result.success and isinstance(result.output, list):
            evidence[key] = result.output[:20]

    return evidence
