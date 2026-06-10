"""Agent for interpreting structured repository scan results."""

from __future__ import annotations

from tools.llm_client import LLMClient

from agents.base_agent import BaseAgent


class RepoAnalyzerAgent(BaseAgent):
    """Explain repository structure and recommend a safe starting point."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Repo Analyzer Agent",
            prompt_path="repo_analyzer_prompt.txt",
            llm_client=llm_client,
        )
