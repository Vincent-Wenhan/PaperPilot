"""Structured multi-paper capability and composition artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PaperCapabilityCard(BaseModel):
    paper_id: str
    title: str = ""
    task: str = ""
    input_type: str = "unknown"
    output_type: str = "unknown"
    core_capability: str = ""
    required_data: list[str] = Field(default_factory=list)
    required_model: str = "unknown"
    metrics: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    possible_product_roles: list[str] = Field(default_factory=list)
    integration_difficulty: str = "medium"
    evidence_from_paper: list[str] = Field(default_factory=list)


class PaperRelationship(BaseModel):
    source_paper_id: str
    target_paper_id: str
    relationship_type: Literal[
        "complementary",
        "redundant",
        "conflicting",
        "dependency",
        "alternative",
    ]
    rationale: str
    integration_notes: list[str] = Field(default_factory=list)


class MethodCompositionPlan(BaseModel):
    strategy: Literal[
        "pipeline",
        "modular",
        "alternative",
        "comparison",
        "agent_workflow",
    ] = "pipeline"
    selected_paper_ids: list[str] = Field(default_factory=list)
    excluded_paper_ids: list[str] = Field(default_factory=list)
    combined_capabilities: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    relationships: list[PaperRelationship] = Field(default_factory=list)
    rationale: str = ""
    risks: list[str] = Field(default_factory=list)


class ResearchSynthesis(BaseModel):
    capability_cards: list[PaperCapabilityCard] = Field(default_factory=list)
    capability_map: dict[str, list[str]] = Field(default_factory=dict)
    composition_plan: MethodCompositionPlan = Field(
        default_factory=MethodCompositionPlan
    )
    summary: str = ""
