"""Shared implementation for language-model-backed PaperPilot agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import PROMPTS_DIR
from tools.llm_client import LLMClient, LLMClientError


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

    @staticmethod
    def _load_json_lenient(raw_text: str) -> Any:
        """Parse JSON while tolerating unescaped control characters in strings."""
        return json.loads(raw_text, strict=False)

    @staticmethod
    def parse_json_response(raw_text: str, schema: type[BaseModel]):
        """Try to parse LLM output as JSON matching a Pydantic schema.

        Returns (parsed_model, None) on success, (None, error_string) on failure.
        """
        import json as _json
        from pydantic import ValidationError

        if not raw_text or not raw_text.strip():
            return None, "Empty response."

        try:
            data = BaseAgent._load_json_lenient(raw_text)
            return schema.model_validate(data), None
        except (_json.JSONDecodeError, ValidationError) as e:
            return None, str(e)

    @staticmethod
    def repair_json_output(raw_text: str, schema: type[BaseModel]):
        """Retry JSON parsing with simple repairs for common LLM output issues.

        Tries in order:
        1. Direct parse (via parse_json_response)
        2. Extract JSON from markdown code blocks (```json ... ```)
        3. Find first { ... } block in the text

        Returns (parsed_model, None) or (None, error_string).
        """
        import json as _json
        import re
        from pydantic import ValidationError

        if not raw_text or not raw_text.strip():
            return None, "Empty response."

        # Attempt 1: direct parse
        model, error = BaseAgent.parse_json_response(raw_text, schema)
        if model is not None:
            return model, None

        # Attempt 2: extract from markdown code blocks
        code_match = re.search(
            r"```(?:json)?\s*\n?(.*?)```",
            raw_text,
            re.DOTALL,
        )
        if code_match:
            try:
                data = BaseAgent._load_json_lenient(code_match.group(1).strip())
                return schema.model_validate(data), None
            except (_json.JSONDecodeError, ValidationError):
                pass

        # Attempt 3: find first { ... } block
        brace_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if brace_match:
            try:
                data = BaseAgent._load_json_lenient(brace_match.group(0))
                return schema.model_validate(data), None
            except (_json.JSONDecodeError, ValidationError):
                pass

        return None, error

    def run(self, input_data: dict[str, Any] | str) -> str:
        """Generate a text result while containing agent-level failures."""
        try:
            user_prompt = self._format_input(input_data)
            result = self.llm_client.generate(self.system_prompt, user_prompt)
            if not isinstance(result, str) or not result.strip():
                return f"{self.name} failed: LLM returned an empty result."
            return result
        except LLMClientError:
            raise
        except Exception as exc:
            return f"{self.name} failed: {exc}"
