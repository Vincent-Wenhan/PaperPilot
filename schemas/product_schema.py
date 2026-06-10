"""Schema for product opportunity scoring."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ProductOpportunity(BaseModel):
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
    overall_score: float
    reason: str


class ProductOpportunityList(BaseModel):
    opportunities: List[ProductOpportunity]
