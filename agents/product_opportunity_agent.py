"""Product opportunity analysis agent."""

from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.product_mock_outputs import PRODUCT_OPPORTUNITY_MOCK
from agents.schema_display import opportunities_to_markdown
from schemas.product_schema import ProductOpportunityList
from tools.llm_client import LLMClient


class ProductOpportunityAgent(BaseAgent):
    """Identify realistic application opportunities for paper technology."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Product Opportunity Agent",
            prompt_path="product_opportunity_prompt.txt",
            llm_client=llm_client,
        )

    def run(self, input_data: dict[str, object] | str) -> str:
        if self.llm_client.mock_mode:
            try:
                self._format_input(input_data)
            except Exception as exc:
                return f"{self.name} failed: {exc}"
            return PRODUCT_OPPORTUNITY_MOCK
        raw = super().run(input_data)
        model, error = self.repair_json_output(raw, ProductOpportunityList)
        if model is not None:
            return opportunities_to_markdown(model)
        repair_suffix = (
            f"\n\nYour previous output could not be parsed as JSON ({error}). "
            "Output ONLY valid JSON matching the required schema."
        )
        raw2 = self.llm_client.generate(
            self.system_prompt + repair_suffix,
            self._format_input(input_data),
        )
        model2, _ = self.repair_json_output(raw2, ProductOpportunityList)
        if model2 is not None:
            return opportunities_to_markdown(model2)
        return raw
