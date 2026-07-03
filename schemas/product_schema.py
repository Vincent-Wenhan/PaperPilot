"""Schema for product opportunity scoring."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductOpportunity(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    idea_name: str
    target_user: str
    core_value: str
    technical_feasibility: int = Field(ge=1, le=5)
    demo_feasibility: int = Field(ge=1, le=5)
    model_availability: int = Field(ge=1, le=5)
    data_requirement: int = Field(ge=1, le=5)
    integration_risk: int = Field(ge=1, le=5)
    user_value: int = Field(ge=1, le=5)
    course_presentation_value: int = Field(ge=1, le=5)
    paper_faithfulness: int = Field(default=3, ge=1, le=5)
    multi_paper_coherence: int = Field(default=3, ge=1, le=5)
    mock_first_suitability: int = Field(default=3, ge=1, le=5)
    overall_score: float = Field(ge=0, le=5)
    reason: str


class ProductOpportunityList(BaseModel):
    opportunities: List[ProductOpportunity]


class ValueProposition(BaseModel):
    customer_jobs: list[str] = Field(default_factory=list)
    pains: list[str] = Field(default_factory=list)
    gains: list[str] = Field(default_factory=list)
    pain_relievers: list[str] = Field(default_factory=list)
    gain_creators: list[str] = Field(default_factory=list)
    product_features: list[str] = Field(default_factory=list)


class PRD(BaseModel):
    product_name: str
    problem_statement: str
    target_users: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    core_features: list[str] = Field(default_factory=list)
    user_flow: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class MVPScope(BaseModel):
    must_have: list[str] = Field(default_factory=list)
    should_have: list[str] = Field(default_factory=list)
    could_have: list[str] = Field(default_factory=list)
    wont_have: list[str] = Field(default_factory=list)


class ProductPlan(BaseModel):
    jtbd: str
    value_proposition: ValueProposition = Field(default_factory=ValueProposition)
    opportunities: list[ProductOpportunity] = Field(default_factory=list)
    selected_product: str
    selection_reason: str
    prd: PRD
    mvp_scope: MVPScope = Field(default_factory=MVPScope)
    risks: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ProductIOContract(BaseModel):
    input_type: Literal["image", "text", "video", "file", "mixed"] = "mixed"
    input_fields: list[str] = Field(default_factory=list)
    output_fields: list[str] = Field(default_factory=list)
    example_input: dict[str, object] = Field(default_factory=dict)
    example_output: dict[str, object] = Field(default_factory=dict)


class ProductUXContract(BaseModel):
    primary_user_action: str = "Run analysis"
    required_controls: list[str] = Field(default_factory=list)
    required_result_cards: list[str] = Field(default_factory=list)
    empty_state: str = "Provide input to start."
    loading_state: str = "Running mock analysis."
    error_state: str = "The mock workflow could not complete."


class ProductSafetyContract(BaseModel):
    forbidden_claims: list[str] = Field(default_factory=list)
    required_disclaimers: list[str] = Field(default_factory=list)
    mock_mode_boundary: str = "Mock mode returns deterministic demo data only."


class ProductContract(BaseModel):
    product_name: str = ""
    target_user: str = ""
    job_to_be_done: str = ""
    io: ProductIOContract = Field(default_factory=ProductIOContract)
    ux: ProductUXContract = Field(default_factory=ProductUXContract)
    safety: ProductSafetyContract = Field(default_factory=ProductSafetyContract)
    acceptance_tests: list[str] = Field(default_factory=list)


class ProductIssue(BaseModel):
    issue_id: str = ""
    category: Literal[
        "paper_faithfulness",
        "user_value",
        "mvp_scope",
        "mock_boundary",
        "ui_usability",
        "technical_feasibility",
        "safety",
    ] = "user_value"
    severity: Literal["low", "medium", "high"] = "medium"
    blocking: bool = False
    message: str = ""
    suggested_route: Literal[
        "revise_prd",
        "reduce_mvp_scope",
        "revise_prototype",
        "accept_with_warning",
    ] = "accept_with_warning"


class ProductVerificationReport(BaseModel):
    ok: bool = False
    score: float = Field(default=0, ge=0, le=5)
    issues: list[ProductIssue] = Field(default_factory=list)
    revision_route: str = "accept_with_warning"


class PrototypePlan(BaseModel):
    template_type: str = "file"
    page_structure: list[str] = Field(default_factory=list)
    user_inputs: list[str] = Field(default_factory=list)
    system_outputs: list[str] = Field(default_factory=list)
    mock_result: dict[str, object] = Field(default_factory=dict)
    real_integration_placeholder: str = ""
    adapter_boundary: list[str] = Field(default_factory=list)
    generated_files: list["PrototypeFileSpec"] = Field(default_factory=list)
    backend_endpoints: list["PrototypeEndpointSpec"] = Field(default_factory=list)
    dependencies: list["PrototypeDependencySpec"] = Field(default_factory=list)
    run_commands: list[str] = Field(default_factory=list)
    mock_first: bool = True


class PrototypeFileSpec(BaseModel):
    path: str = ""
    purpose: str = ""
    content: str = ""
    role: str = "support"


class PrototypeEndpointSpec(BaseModel):
    path: str = ""
    method: str = "GET"
    purpose: str = ""


class PrototypeDependencySpec(BaseModel):
    name: str = ""
    version: str = ""
    kind: str = "python"


class UIControl(BaseModel):
    control_id: str = ""
    label: str = ""
    control_type: str = "text_input"
    default: object | None = None
    options: list[str] = Field(default_factory=list)
    help_text: str = ""
    required: bool = False


class ResultComponent(BaseModel):
    component_id: str = ""
    label: str = ""
    component_type: str = "summary"
    source_key: str = ""
    description: str = ""


class UIStateCopy(BaseModel):
    empty: str = "Provide an input to start the mock workflow."
    loading: str = "Running mock analysis."
    success: str = "Mock analysis completed."
    error: str = "The mock workflow could not complete."


class ProductUISpec(BaseModel):
    product_name: str = ""
    template_type: str = "file"
    layout_mode: str = "workflow_dashboard"
    page_sections: list[str] = Field(default_factory=list)
    input_controls: list[UIControl] = Field(default_factory=list)
    result_components: list[ResultComponent] = Field(default_factory=list)
    mock_result_schema: dict[str, str] = Field(default_factory=dict)
    states: UIStateCopy = Field(default_factory=UIStateCopy)
    visual_rules: list[str] = Field(default_factory=list)


class ProductProposal(BaseModel):
    """One complete product proposal, used in the proposal review stage."""
    product_name: str = ""
    target_user: str = ""
    product_goal: str = ""
    jtbd: str = ""
    opportunities: list[ProductOpportunity] = Field(default_factory=list)
    value_proposition: ValueProposition = Field(default_factory=ValueProposition)
    prd: PRD = Field(default_factory=PRD)
    mvp_scope: MVPScope = Field(default_factory=MVPScope)
    risks: list[str] = Field(default_factory=list)
