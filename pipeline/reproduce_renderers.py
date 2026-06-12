"""Deterministic Markdown renderers for structured Reproduce artifacts."""

from __future__ import annotations

from schemas.reproduction_schema import (
    ExecutionDiagnosis,
    ImplementationBundle,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
)


def _bullets(items: list[str], empty: str = "Not specified.") -> str:
    return "\n".join(f"- {item}" for item in items) if items else f"- {empty}"


def _evidence(items: list[str]) -> str:
    return "; ".join(items) if items else "No page-specific evidence recorded."


def _render_method_modules(model: PaperUnderstanding) -> str:
    if not model.method_modules:
        return "- Not specified."
    sections: list[str] = []
    for module in model.method_modules:
        sections.append(
            f"""### {module.name or "Unnamed Module"}

**Purpose:** {module.purpose or "Not specified."}

**Inputs:** {", ".join(module.inputs) or "Not specified."}

**Outputs:** {", ".join(module.outputs) or "Not specified."}

**Mechanism**
{_bullets(module.mechanism)}

**Trainable Components**
{_bullets(module.trainable_components)}

**Implementation Notes**
{_bullets(module.implementation_notes)}

**Evidence:** {_evidence(module.evidence)}"""
        )
    return "\n\n".join(sections)


def _render_datasets(model: PaperUnderstanding) -> str:
    if not model.datasets:
        return "- Not specified."
    return "\n".join(
        f"- **{item.name}**: {item.role or 'Role not specified.'} "
        f"Input: {item.input_format or 'unknown'}. Evidence: {_evidence(item.evidence)}"
        for item in model.datasets
    )


def _render_metrics(model: PaperUnderstanding) -> str:
    if not model.metrics:
        return "- Not specified."
    return "\n".join(
        f"- **{item.name}**: {item.purpose or 'Purpose not specified.'} "
        f"{item.interpretation} Evidence: {_evidence(item.evidence)}"
        for item in model.metrics
    )


def _render_resource_links(items: list[object]) -> str:
    if not items:
        return "- No evidence-backed download links found."
    return "\n".join(
        f"- **{item.name or item.resource_type}** ({item.resource_type}): "
        f"`{item.url}` -> `{item.destination}`; source: {item.source or 'unknown'}"
        for item in items
    )


def render_research_summary(model: PaperUnderstanding) -> str:
    """Render the paper-summary compatibility field."""
    return f"""# {model.title or "Research Understanding"}

**Task:** {model.task or "Not specified."}

**Problem:** {model.problem or "Not specified."}

## Contributions
{_bullets(model.contributions)}

## Method Summary
{model.method_summary or "Not specified."}

## Datasets
{_render_datasets(model)}

## Metrics
{_render_metrics(model)}

## Evidence-Backed Resource Links
{_render_resource_links(model.resource_links)}
"""


def render_method_breakdown(model: PaperUnderstanding) -> str:
    """Render the method-breakdown compatibility field."""
    return f"""# Method Breakdown

## Method Modules
{_render_method_modules(model)}

## End-to-End Dataflow
{_bullets(model.end_to_end_dataflow)}

## Objective Terms
{_bullets([
    f"{item.name}: {item.formula_or_description} ({item.optimization_role}) Evidence: {_evidence(item.evidence)}"
    for item in model.objectives
])}

## Training Details
{_bullets(model.training_details)}

## Inference Details
{_bullets(model.inference_details)}

## Experiment Findings
{_bullets([
    f"{item.question} | Setup: {item.setup} | Result: {item.result} | Conclusion: {item.conclusion} | Evidence: {_evidence(item.evidence)}"
    for item in model.experiment_findings
])}

## Baseline Differences
{_bullets(model.baseline_differences)}

## Implementation Blueprint
{_bullets(model.implementation_blueprint)}

## Reproduction Clues
{_bullets(model.reproduction_clues)}

## Paper Evidence
{_bullets(model.evidence)}

## Missing Information
{_bullets(model.missing_information)}
"""


def render_repository_understanding(model: RepositoryUnderstanding) -> str:
    """Render repository evidence and risks."""
    return f"""# Repository Understanding

**Source:** {model.repo_source}

**Framework:** {model.detected_framework}

## Dependency Files
{_bullets(model.dependency_files)}

## Config Files
{_bullets(model.config_files)}

## Minimal Runnable Candidates
{_bullets(model.minimal_runnable_candidates)}

## Evidence-Backed Resource Links
{_render_resource_links(model.resource_links)}

## Risk Signals
{_bullets(model.risk_signals)}

## Notes
{_bullets(model.notes)}
"""


def render_environment_plan(model: ReproductionPlan) -> str:
    """Render environment and data preparation guidance."""
    return f"""# Environment and Data Plan

## Environment
{_bullets(model.environment_plan)}

## Data Preparation
{_bullets(model.data_preparation_plan)}
"""


def render_experiment_plan(model: ReproductionPlan) -> str:
    """Render minimal/full reproduction and fallback steps."""
    return f"""# Reproduction and Implementation Plan

## Implementation Strategy
{model.implementation_strategy or "Not specified."}

## Architecture Plan
{_bullets(model.architecture_plan)}

## Minimal Reproduction
{_bullets(model.minimal_reproduction_steps)}

## Full Reproduction
{_bullets(model.full_reproduction_steps)}

## Acceptance Criteria
{_bullets(model.acceptance_criteria)}

## Validation Plan
{_bullets(model.validation_plan)}

## Risks
{_bullets(model.risks)}

## Fallback Plan
{_bullets(model.fallback_plan)}
"""


def render_execution_diagnosis(model: ExecutionDiagnosis) -> str:
    """Render execution status and diagnosis."""
    return f"""# Execution & Diagnosis

**Feasibility:** {model.feasibility}

**Direct Cause / Status:** {model.direct_cause or "Not specified."}

## Possible Root Causes
{_bullets(model.possible_root_causes)}

## Suggested Fixes
{_bullets(model.suggested_fixes)}

## Next Actions
{_bullets(model.next_actions)}
"""


def render_implementation_summary(
    model: ImplementationBundle,
    repo_path: str,
    files: list[str],
    implementation_model: str = "",
) -> str:
    """Render generated implementation scope and usage."""
    return f"""# Generated Reproduction Implementation

**Project:** {model.project_name}

**Local Path:** `{repo_path}`

**Implementation Model:** {implementation_model or "Not recorded."}

**Summary:** {model.summary or "Not specified."}

## Fidelity Scope
{_bullets(model.fidelity_scope)}

## Assumptions
{_bullets(model.assumptions)}

## Data and Checkpoint Resources
{_render_resource_links(model.data_resources)}

## Data Download Command
`{model.data_download_command or "No evidence-backed resource link was found; no download script generated."}`

## Generated Files
{_bullets([f"`{path}`" for path in files])}

## Smoke Test
`{model.smoke_test_command}`

**Expected Output:** {model.expected_smoke_test_output or "Not specified."}
"""
