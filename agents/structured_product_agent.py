"""Base class for guideline-backed structured Productize agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from agents.base_agent import BaseAgent
from tools.guideline_loader import load_guidelines
from tools.llm_client import LLMClient

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class StructuredProductAgent(BaseAgent, ABC, Generic[SchemaT]):
    """Return schema-valid output and use deterministic mock fallbacks."""

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
            f"{json.dumps(schema_type.model_json_schema(), indent=2)}"
        )

    @abstractmethod
    def build_mock(self, input_data: dict[str, Any]) -> SchemaT:
        """Build a deterministic schema-valid fallback."""

    def run_structured(self, input_data: dict[str, Any]) -> SchemaT:
        """Run the agent and always return a schema-valid artifact."""
        self._format_input(input_data)
        if self.llm_client.mock_mode:
            return self.build_mock(input_data)

        raw = super().run(input_data)
        parsed, _ = self.repair_json_output(raw, self.schema_type)
        if parsed is not None:
            return parsed
        return self.build_mock(input_data)
