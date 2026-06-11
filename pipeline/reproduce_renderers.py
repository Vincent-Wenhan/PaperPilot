"""Deterministic Markdown renderers for structured Reproduce artifacts."""

from __future__ import annotations

from schemas.reproduction_schema import (
    ExecutionDiagnosis,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
)


def _bullets(items: list[str], empty: str = "Not specified.") -> str:
    return "\n".join(f"- {item}" for item in items) if items else f"- {empty}"


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
{_bullets(model.datasets)}

## Metrics
{_bullets(model.metrics)}
"""


def render_method_breakdown(model: PaperUnderstanding) -> str:
    """Render the method-breakdown compatibility field."""
    return f"""# Method Breakdown

## Method Modules
{_bullets(model.method_modules)}

## Training Details
{_bullets(model.training_details)}

## Inference Details
{_bullets(model.inference_details)}

## Reproduction Clues
{_bullets(model.reproduction_clues)}

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
    return f"""# Reproduction Steps

## Minimal Reproduction
{_bullets(model.minimal_reproduction_steps)}

## Full Reproduction
{_bullets(model.full_reproduction_steps)}

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
