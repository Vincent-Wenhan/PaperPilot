"""Agent for interpreting structured repository scan results."""

from __future__ import annotations

from typing import Any

from agents.legacy.schema_display import repo_analysis_to_markdown
from schemas.repo_schema import RepoAnalysis
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

    def run(self, input_data: dict[str, Any] | str) -> str:
        raw = super().run(input_data)
        model, error = self.repair_json_output(raw, RepoAnalysis)
        if model is not None:
            return repo_analysis_to_markdown(model)
        repair_suffix = (
            f"\n\nYour previous output could not be parsed as JSON ({error}). "
            "Output ONLY valid JSON matching the required schema."
        )
        raw2 = self.llm_client.generate(
            self.system_prompt + repair_suffix,
            self._format_input(input_data),
        )
        model2, _ = self.repair_json_output(raw2, RepoAnalysis)
        if model2 is not None:
            return repo_analysis_to_markdown(model2)
        return raw
