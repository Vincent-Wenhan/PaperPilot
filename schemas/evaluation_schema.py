"""Rubric-based product evaluation artifacts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProductEvaluation(BaseModel):
    paper_faithfulness: float = Field(default=4, ge=1, le=5)
    multi_paper_coherence: float = Field(default=4, ge=1, le=5)
    user_clarity: float = Field(default=4, ge=1, le=5)
    problem_solution_fit: float = Field(default=4, ge=1, le=5)
    prd_completeness: float = Field(default=4, ge=1, le=5)
    mvp_simplicity: float = Field(default=4, ge=1, le=5)
    demo_feasibility: float = Field(default=4, ge=1, le=5)
    mock_first_correctness: float = Field(default=4, ge=1, le=5)
    safety_awareness: float = Field(default=4, ge=1, le=5)
    integration_feasibility: float = Field(default=4, ge=1, le=5)
    overall_score: float = Field(default=4, ge=1, le=5)
    detected_problems: list[str] = Field(default_factory=list)
    revision_suggestions: list[str] = Field(default_factory=list)
    safety_warnings: list[str] = Field(default_factory=list)
    demo_readiness: str = "ready_with_mock"
