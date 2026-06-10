"""Deterministic agent wrapper for safe GitHub repository cloning."""

from __future__ import annotations

from pathlib import Path

from config import WORKSPACE_DIR
from tools.github_tool import clone_github_repo


class RepoCloneAgent:
    """Clone a validated GitHub repository without executing its code."""

    name = "Repo Clone Agent"

    def __init__(self, workspace_dir: str | Path = WORKSPACE_DIR) -> None:
        self.workspace_dir = Path(workspace_dir).expanduser()

    def clone(self, github_url: str) -> Path:
        """Clone a repository and return its path for pipeline integration."""
        if not github_url.strip():
            raise ValueError("未提供 GitHub 仓库链接。")
        return clone_github_repo(github_url.strip(), self.workspace_dir)

    def run(self, input_data: dict[str, object] | str) -> str:
        """Clone the requested repository and return its local path as text."""
        try:
            if isinstance(input_data, str):
                github_url = input_data.strip()
            elif isinstance(input_data, dict):
                github_url = str(
                    input_data.get("github_url") or input_data.get("url") or ""
                ).strip()
            else:
                raise TypeError("输入必须是 GitHub URL 字符串或字典。")

            repo_path = self.clone(github_url)
            return f"仓库 clone 成功：{repo_path}"
        except Exception as exc:
            return f"{self.name} 执行失败：{exc}"
