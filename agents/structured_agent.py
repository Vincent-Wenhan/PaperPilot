"""Base class for guideline-backed structured reasoning agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
import os
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from agents.base_agent import BaseAgent
from tools.guideline_loader import load_guidelines
from tools.llm_client import LLMClient

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredAgent(BaseAgent, ABC, Generic[SchemaT]):
    """Return schema-valid artifacts or expose invalid real-model responses."""

    def __init__(
        self,
        *,
        name: str,
        prompt_path: str,
        schema_type: type[SchemaT],
        guideline_names: tuple[str, ...],
        llm_client: LLMClient | None = None,
        model: str | None = None,
    ) -> None:
        self.schema_type = schema_type
        if llm_client is None and model is not None:
            llm_client = LLMClient(model=model)
        super().__init__(name=name, prompt_path=prompt_path, llm_client=llm_client)
        self.system_prompt = (
            f"{self.system_prompt}\n\n# Approved Guidelines\n\n"
            f"{load_guidelines(guideline_names)}\n\n# Required JSON Schema\n\n"
            f"{json.dumps(schema_type.model_json_schema(), indent=2)}\n\n"
            "# JSON Encoding Rules\n\n"
            "Return one JSON object only. Escape newlines, tabs, backslashes, and "
            "quotation marks inside JSON string values."
        )

    @abstractmethod
    def build_mock(self, input_data: dict[str, Any]) -> SchemaT:
        """Build a deterministic schema-valid fallback."""

    def validate_structured_result(
        self,
        result: SchemaT,
        input_data: dict[str, Any],
    ) -> str | None:
        """Return a quality-gate error for schema-valid but unusable output."""
        del result, input_data
        return None

    def _parse_structured_response(
        self,
        raw: str,
        input_data: dict[str, Any],
    ) -> tuple[SchemaT | None, str | None]:
        parsed, error = self.repair_json_output(raw, self.schema_type)
        if parsed is None:
            return None, error
        quality_error = self.validate_structured_result(parsed, input_data)
        if quality_error is not None:
            return None, quality_error
        return parsed, None

    def run_structured(self, input_data: dict[str, Any]) -> SchemaT:
        """Run the reasoning stage and require a schema-valid real-model result."""
        formatted_input = self._format_input(input_data)
        if self.llm_client.mock_mode:
            return self.build_mock(input_data)
        raw = self._invoke_llm(formatted_input)
        parsed, error = self._parse_structured_response(raw, input_data)
        if parsed is not None:
            return parsed
        retry_prompt = (
            f"{formatted_input}\n\n"
            "Your previous response was invalid structured JSON. "
            f"Error: {error}. Return ONE JSON object only that matches the schema. "
            "Do not wrap the JSON in markdown fences."
        )
        raw_retry = self._invoke_llm(retry_prompt)
        parsed_retry, retry_error = self._parse_structured_response(
            raw_retry, input_data
        )
        if parsed_retry is not None:
            return parsed_retry
        preview = " ".join(raw_retry.split())[:500]
        raise RuntimeError(
            f"{self.name} returned invalid structured output after retry: {retry_error}. "
            f"Response preview: {preview or '<empty>'}"
        )

    def _invoke_llm(self, prompt: str) -> str:
        """Call the LLM client, tolerating older ``generate`` signatures.

        Tests inject mock clients whose ``generate`` only accepts positional
        args. Try keyword args first, fall back to positional.
        """
        max_tokens = self._max_output_tokens()
        try:
            return self.llm_client.generate(
                self.system_prompt,
                prompt,
                max_tokens=max_tokens,
                json_mode=True,
            )
        except TypeError:
            return self.llm_client.generate(self.system_prompt, prompt)

    def _max_output_tokens(self) -> int | None:
        """Cap output tokens for structured agents to avoid truncation.

        Reads ``LLM_MAX_OUTPUT_TOKENS`` (default 8192) so callers can tune
        per-deployment without code changes. Set to 0 to disable the cap.
        """
        raw = os.getenv("LLM_MAX_OUTPUT_TOKENS", "8192")
        try:
            value = int(raw)
        except ValueError:
            return 8192
        return value or None
