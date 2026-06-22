"""High-level prototype planning agent."""

from __future__ import annotations

from typing import Any

from agents.structured_agent import StructuredAgent
from schemas.product_schema import ProductPlan, PrototypePlan
from tools.llm_client import LLMClient


class PrototypeBuilderAgent(StructuredAgent[PrototypePlan]):
    """Define the bounded product prototype and adapter boundary."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Prototype Builder Agent",
            prompt_path="prototype_builder_prompt.txt",
            schema_type=PrototypePlan,
            guideline_names=(
                "frontend_prototype_rules.md",
                "mvp_scope_rules.md",
                "evidence_traceability_rules.md",
                "confidence_and_limitations_rules.md",
                "adapter_integration_rules.md",
                "safety_rules.md",
            ),
            llm_client=llm_client,
        )

    def build_mock(self, input_data: dict[str, Any]) -> PrototypePlan:
        product_plan = ProductPlan.model_validate(input_data.get("product_plan") or {})
        template_type = str(input_data.get("template_type") or "file")
        return PrototypePlan(
            template_type=template_type,
            page_structure=[
                "Product purpose and limitations",
                "Input and primary action",
                "Structured result",
                "Evidence, scope, and evaluation",
            ],
            user_inputs=[f"{template_type} input", "Optional product context"],
            system_outputs=["Structured mock result", "Downloadable JSON"],
            mock_result={
                "product": product_plan.selected_product,
                "status": "mock result",
            },
            real_integration_placeholder=(
                "Implement reviewed preprocessing, inference, and output conversion "
                "inside ModelAdapter."
            ),
            adapter_boundary=[
                "setup() validates reviewed configuration",
                "load_model() is manual outside mock mode",
                "predict() converts one bounded input to structured output",
            ],
            backend_endpoints=[
                {
                    "path": "/health",
                    "method": "GET",
                    "purpose": "Check generated backend readiness",
                },
                {
                    "path": "/predict",
                    "method": "POST",
                    "purpose": "Run mock-first model adapter prediction",
                },
            ],
            dependencies=[
                {"name": "fastapi", "version": ">=0.115,<1", "kind": "python"},
                {"name": "uvicorn[standard]", "version": ">=0.30,<1", "kind": "python"},
            ],
            run_commands=[
                "python -m pip install -r requirements.txt",
                "python -m uvicorn backend.main:app --reload --port 8000",
                "python -m http.server 8080 -d frontend",
            ],
            mock_first=True,
        )
