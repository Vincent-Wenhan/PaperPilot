"""Helpers for converting Pydantic schemas to Markdown display text."""

from __future__ import annotations

from schemas.paper_schema import PaperSummary
from schemas.repo_schema import RepoAnalysis
from schemas.product_schema import ProductOpportunityList


def paper_summary_to_markdown(m: PaperSummary) -> str:
    """Convert a PaperSummary schema to human-readable Markdown."""
    lines = [f"# {m.title or 'Paper Summary'}", ""]
    if m.task:
        lines.append(f"**Task:** {m.task}")
    if m.problem:
        lines.append(f"**Problem:** {m.problem}")
    if m.contributions:
        lines.append("")
        lines.append("## Contributions")
        lines.extend(f"- {c}" for c in m.contributions)
    if m.method_summary:
        lines.append("")
        lines.append(f"## Method\n\n{m.method_summary}")
    if m.datasets:
        lines.append("")
        lines.append("## Datasets")
        lines.extend(f"- {d}" for d in m.datasets)
    if m.metrics:
        lines.append("")
        lines.append("## Metrics")
        lines.extend(f"- {m}" for m in m.metrics)
    if m.training_details:
        lines.append("")
        lines.append("## Training Details")
        lines.extend(f"- {t}" for t in m.training_details)
    if m.limitations:
        lines.append("")
        lines.append("## Limitations")
        lines.extend(f"- {l}" for l in m.limitations)
    return "\n".join(lines)


def repo_analysis_to_markdown(m: RepoAnalysis) -> str:
    """Convert a RepoAnalysis schema to human-readable Markdown."""
    lines = ["# Repository Analysis", ""]
    lines.append(f"**Framework:** {m.framework}")
    lines.append(f"**Task Type:** {m.task_type}")
    lines.append(f"**Risk Level:** {m.risk_level}")
    if m.training_entrypoints:
        lines.append("")
        lines.append("## Training Entrypoints")
        lines.extend(f"- `{e}`" for e in m.training_entrypoints)
    if m.inference_entrypoints:
        lines.append("")
        lines.append("## Inference Entrypoints")
        lines.extend(f"- `{e}`" for e in m.inference_entrypoints)
    if m.config_files:
        lines.append("")
        lines.append("## Config Files")
        lines.extend(f"- `{f}`" for f in m.config_files)
    if m.dependency_files:
        lines.append("")
        lines.append("## Dependency Files")
        lines.extend(f"- `{f}`" for f in m.dependency_files)
    if m.dataset_requirements:
        lines.append("")
        lines.append("## Dataset Requirements")
        lines.extend(f"- {d}" for d in m.dataset_requirements)
    if m.checkpoint_requirements:
        lines.append("")
        lines.append("## Checkpoint Requirements")
        lines.extend(f"- {c}" for c in m.checkpoint_requirements)
    if m.notes:
        lines.append("")
        lines.append("## Notes")
        lines.extend(f"- {n}" for n in m.notes)
    return "\n".join(lines)


def opportunities_to_markdown(m: ProductOpportunityList) -> str:
    """Convert a ProductOpportunityList schema to human-readable Markdown."""
    if not m.opportunities:
        return "# Product Opportunities\n\nNo opportunities identified."
    lines = []
    for i, opp in enumerate(m.opportunities, 1):
        lines.append(f"## Opportunity {i}: {opp.idea_name}")
        lines.append("")
        lines.append(f"**Target User:** {opp.target_user}")
        lines.append(f"**Core Value:** {opp.core_value}")
        lines.append(f"**Overall Score:** {opp.overall_score}")
        lines.append("")
        lines.append("### Scoring")
        lines.append(f"- Technical Feasibility: {opp.technical_feasibility}/5")
        lines.append(f"- Demo Feasibility: {opp.demo_feasibility}/5")
        lines.append(f"- Model Availability: {opp.model_availability}/5")
        lines.append(f"- Data Requirement: {opp.data_requirement}/5")
        lines.append(f"- Integration Risk: {opp.integration_risk}/5")
        lines.append(f"- User Value: {opp.user_value}/5")
        lines.append(f"- Course Presentation Value: {opp.course_presentation_value}/5")
        lines.append("")
        lines.append(f"**Reason:** {opp.reason}")
        lines.append("")
    return "\n".join(lines)
