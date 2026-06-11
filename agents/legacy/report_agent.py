"""Agent for generating the final paper reproduction report."""

from __future__ import annotations

from tools.llm_client import LLMClient

from agents.base_agent import BaseAgent


class ReportAgent(BaseAgent):
    """Combine pipeline results into a structured course-project report."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Report Agent",
            prompt_path="report_prompt.txt",
            llm_client=llm_client,
        )
