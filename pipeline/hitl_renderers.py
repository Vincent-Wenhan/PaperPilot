"""Deterministic renderers for HITL confirmation nodes."""

from __future__ import annotations

from schemas.composition_schema import ResearchSynthesis


def render_capability_cards(synthesis: ResearchSynthesis) -> str:
    """Render capability cards, capability map, and composition plan for HITL."""
    lines = ["# Capability Cards"]
    for card in synthesis.capability_cards:
        lines.extend([
            f"## {card.title or card.paper_id}",
            f"**Task:** {card.task}",
            f"**Core Capability:** {card.core_capability}",
            f"**Input/Output:** {card.input_type} → {card.output_type}",
            "**Strengths:**",
            *[f"- {s}" for s in card.strengths],
            "**Limitations:**",
            *[f"- {l}" for l in card.limitations],
            "**Possible Product Roles:**",
            *[f"- {r}" for r in card.possible_product_roles],
            "",
        ])

    lines.append("## Capability Map")
    if synthesis.capability_map:
        for key, values in synthesis.capability_map.items():
            lines.append(f"- **{key}:** {', '.join(values) if isinstance(values, list) else values}")
    else:
        lines.append("- Not specified.")
    lines.append("")

    lines.append("## Composition Plan")
    plan = synthesis.composition_plan
    lines.append(f"**Strategy:** {plan.strategy}")
    lines.append(f"**Rationale:** {plan.rationale or 'Not specified.'}")
    if plan.workflow_steps:
        lines.append("**Workflow Steps:**")
        lines.extend(f"- {step}" for step in plan.workflow_steps)
    if plan.risks:
        lines.append("**Risks:**")
        lines.extend(f"- {risk}" for risk in plan.risks)

    return "\n".join(lines)
