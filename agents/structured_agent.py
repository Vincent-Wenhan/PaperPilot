"""Base class for guideline-backed structured reasoning agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
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
    ) -> None:
        self.schema_type = schema_type
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

    def run_structured(self, input_data: dict[str, Any]) -> SchemaT:
        """Run the reasoning stage and require a schema-valid real-model result."""
        self._format_input(input_data)
        if self.llm_client.mock_mode:
            return self.build_mock(input_data)
        raw = super().run(input_data)
        parsed, error = self.repair_json_output(raw, self.schema_type)
        if parsed is not None:
            quality_error = self.validate_structured_result(parsed, input_data)
            if quality_error is None:
                return parsed
            error = quality_error
        preview = " ".join(raw.split())[:500]
        raise RuntimeError(
            f"{self.name} returned invalid structured output: {error}. "
            f"Response preview: {preview or '<empty>'}"
        )
