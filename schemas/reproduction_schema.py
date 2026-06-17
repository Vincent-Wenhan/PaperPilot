"""Structured artifacts for the converged Reproduce pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.runner_schema import CommandPlan


class ResourceLink(BaseModel):
    name: str = ""
    url: str = ""
    resource_type: str = "dataset"
    destination: str = "data/resource.bin"
    source: str = ""
    evidence: str = ""


class HyperParameter(BaseModel):
    name: str = ""
    value: str = ""
    evidence: list[str] = Field(default_factory=list)


class MethodModule(BaseModel):
    name: str = ""
    purpose: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    mechanism: list[str] = Field(default_factory=list)
    trainable_components: list[str] = Field(default_factory=list)
    implementation_notes: list[str] = Field(default_factory=list)
    loss_formula: str = ""
    input_shape: str = ""
    output_shape: str = ""
    hyperparameters: list[HyperParameter] = Field(default_factory=list)
    initialization: str = ""
    architecture_details: str = ""
    evidence: list[str] = Field(default_factory=list)


class MethodSpec(BaseModel):
    """Pseudo-code spec bridging paper understanding to implementation."""
    model_name: str = ""
    input_shape: str = ""
    output_shape: str = ""
    loss_formulas: list[str] = Field(default_factory=list)
    forward_pass_pseudocode: list[str] = Field(default_factory=list)
    training_step_pseudocode: list[str] = Field(default_factory=list)
    hyperparameters: list[HyperParameter] = Field(default_factory=list)
    initialization: str = ""
    optimizer: str = ""
    architecture_modules: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)
    implementation_notes: list[str] = Field(default_factory=list)


class ObjectiveTerm(BaseModel):
    name: str = ""
    formula_or_description: str = ""
    optimization_role: str = ""
    evidence: list[str] = Field(default_factory=list)


class DatasetAnalysis(BaseModel):
    name: str = ""
    role: str = ""
    input_format: str = ""
    preprocessing: list[str] = Field(default_factory=list)
    split_or_scale: str = ""
    evidence: list[str] = Field(default_factory=list)


class MetricAnalysis(BaseModel):
    name: str = ""
    purpose: str = ""
    interpretation: str = ""
    evidence: list[str] = Field(default_factory=list)


class ExperimentFinding(BaseModel):
    question: str = ""
    setup: str = ""
    result: str = ""
    conclusion: str = ""
    evidence: list[str] = Field(default_factory=list)


class PaperUnderstanding(BaseModel):
    title: str = ""
    task: str = ""
    problem: str = ""
    contributions: list[str] = Field(default_factory=list)
    method_summary: str = ""
    method_modules: list[MethodModule] = Field(default_factory=list)
    end_to_end_dataflow: list[str] = Field(default_factory=list)
    objectives: list[ObjectiveTerm] = Field(default_factory=list)
    datasets: list[DatasetAnalysis] = Field(default_factory=list)
    metrics: list[MetricAnalysis] = Field(default_factory=list)
    training_details: list[str] = Field(default_factory=list)
    inference_details: list[str] = Field(default_factory=list)
    experiment_findings: list[ExperimentFinding] = Field(default_factory=list)
    baseline_differences: list[str] = Field(default_factory=list)
    implementation_blueprint: list[str] = Field(default_factory=list)
    resource_links: list[ResourceLink] = Field(default_factory=list)
    reproduction_clues: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
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
    resource_links: list[ResourceLink] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    minimal_runnable_candidates: list[str] = Field(default_factory=list)
    environment_evidence: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ReproductionPlan(BaseModel):
    goal: str = "minimal training experiment"
    implementation_strategy: str = ""
    architecture_plan: list[str] = Field(default_factory=list)
    environment_plan: list[str] = Field(default_factory=list)
    data_preparation_plan: list[str] = Field(default_factory=list)
    minimal_reproduction_steps: list[str] = Field(default_factory=list)
    full_reproduction_steps: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    validation_plan: list[str] = Field(default_factory=list)
    command_plans: list[CommandPlan] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    fallback_plan: list[str] = Field(default_factory=list)


class GeneratedCodeFile(BaseModel):
    path: str = ""
    purpose: str = ""
    content: str = ""


class ImplementationBundle(BaseModel):
    project_name: str = "paperpilot_reproduction"
    summary: str = ""
    fidelity_scope: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    data_resources: list[ResourceLink] = Field(default_factory=list)
    files: list[GeneratedCodeFile] = Field(default_factory=list)
    data_download_command: str = ""
    smoke_test_command: str = "python main.py --smoke-test"
    expected_smoke_test_output: str = ""


class ExecutionDiagnosis(BaseModel):
    command: str = ""
    executed: bool = False
    exit_code: int | None = None
    direct_cause: str = ""
    possible_root_causes: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    feasibility: str = "planned_not_executed"
