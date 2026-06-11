"""Schema for product opportunity scoring."""
from __future__ import annotations

from typing import List

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


class PrototypePlan(BaseModel):
    template_type: str = "file"
    page_structure: list[str] = Field(default_factory=list)
    user_inputs: list[str] = Field(default_factory=list)
    system_outputs: list[str] = Field(default_factory=list)
    mock_result: dict[str, object] = Field(default_factory=dict)
    real_integration_placeholder: str = ""
    adapter_boundary: list[str] = Field(default_factory=list)
    mock_first: bool = True


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
