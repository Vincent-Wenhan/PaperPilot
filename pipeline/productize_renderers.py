"""Deterministic renderers for structured Productize artifacts."""

from __future__ import annotations

from schemas.product_schema import ProductOpportunityList


def render_opportunities(model: ProductOpportunityList) -> str:
    """Render structured product opportunities as Markdown."""
    if not model.opportunities:
        return "# Product Opportunities\n\nNo opportunities identified."
    lines = ["# Product Opportunities", ""]
    for index, opportunity in enumerate(model.opportunities, 1):
        lines.extend(
            [
                f"## {index}. {opportunity.idea_name}",
                "",
                f"**Target User:** {opportunity.target_user}",
                f"**Core Value:** {opportunity.core_value}",
                f"**Overall Score:** {opportunity.overall_score}/5",
                f"**Reason:** {opportunity.reason}",
                "",
            ]
        )
    return "\n".join(lines)
