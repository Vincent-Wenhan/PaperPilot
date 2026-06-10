"""Shared implementation for language-model-backed PaperPilot agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import PROMPTS_DIR
from tools.llm_client import LLMClient


class BaseAgent:
    """Load a system prompt and execute a request through one LLM client."""

    def __init__(
        self,
        name: str,
        prompt_path: str | Path,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.name = name
        self.prompt_path = self._resolve_prompt_path(prompt_path)
        self.llm_client = llm_client or LLMClient()
        self.system_prompt = self._load_prompt()

    @staticmethod
    def _resolve_prompt_path(prompt_path: str | Path) -> Path:
        path = Path(prompt_path).expanduser()
        if not path.is_absolute():
            path = PROMPTS_DIR / path
        return path.resolve()

    def _load_prompt(self) -> str:
        if not self.prompt_path.is_file():
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_path}")
        try:
            prompt = self.prompt_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Failed to read prompt file: {exc}") from exc
        if not prompt:
            raise ValueError(f"Prompt file is empty: {self.prompt_path}")
        return prompt

    @staticmethod
    def _format_input(input_data: dict[str, Any] | str) -> str:
        if isinstance(input_data, str):
            text = input_data.strip()
            if not text:
                raise ValueError("Input cannot be empty.")
            return text
        if isinstance(input_data, dict):
            if not input_data:
                raise ValueError("Input dict cannot be empty.")
            return json.dumps(
                input_data,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        raise TypeError("Input must be a string or a dict.")

    def run(self, input_data: dict[str, Any] | str) -> str:
        """Generate a text result while containing agent-level failures."""
        try:
            user_prompt = self._format_input(input_data)
            result = self.llm_client.generate(self.system_prompt, user_prompt)
            if not isinstance(result, str) or not result.strip():
                return f"{self.name} failed: LLM returned an empty result."
            return result
        except Exception as exc:
            return f"{self.name} failed: {exc}"
