"""Structured artifacts for the converged Reproduce pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.runner_schema import CommandPlan


class PaperUnderstanding(BaseModel):
    title: str = ""
    task: str = ""
    problem: str = ""
    contributions: list[str] = Field(default_factory=list)
    method_summary: str = ""
    method_modules: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    training_details: list[str] = Field(default_factory=list)
    inference_details: list[str] = Field(default_factory=list)
    reproduction_clues: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class RepositoryUnderstanding(BaseModel):
    repo_source: str = "paper-only"
    repo_url: str = ""
    repo_path: str = ""
    detected_framework: str = "unknown"
    dependency_files: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    training_entrypoints: list[str] = Field(default_factory=list)
    evaluation_entrypoints: list[str] = Field(default_factory=list)
    demo_entrypoints: list[str] = Field(default_factory=list)
    dataset_requirements: list[str] = Field(default_factory=list)
    checkpoint_requirements: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    minimal_runnable_candidates: list[str] = Field(default_factory=list)
    environment_evidence: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ReproductionPlan(BaseModel):
    goal: str = "minimal training experiment"
    environment_plan: list[str] = Field(default_factory=list)
    data_preparation_plan: list[str] = Field(default_factory=list)
    minimal_reproduction_steps: list[str] = Field(default_factory=list)
    full_reproduction_steps: list[str] = Field(default_factory=list)
    command_plans: list[CommandPlan] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    fallback_plan: list[str] = Field(default_factory=list)


class ExecutionDiagnosis(BaseModel):
    command: str = ""
    executed: bool = False
    exit_code: int | None = None
    direct_cause: str = ""
    possible_root_causes: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    feasibility: str = "planned_not_executed"
