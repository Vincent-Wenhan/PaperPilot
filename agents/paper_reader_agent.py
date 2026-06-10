"""Agent for extracting reproduction details from paper text."""

from __future__ import annotations

from tools.llm_client import LLMClient

from agents.base_agent import BaseAgent


class PaperReaderAgent(BaseAgent):
    """Summarize paper text with a reproduction-oriented prompt."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Paper Reader Agent",
            prompt_path="paper_reader_prompt.txt",
            llm_client=llm_client,
        )
