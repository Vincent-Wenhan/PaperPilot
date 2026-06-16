"""Structured artifacts for code review in the Reproduce pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CodeReview(BaseModel):
    """Evaluation of generated reproduction code against paper evidence."""

    paper_fidelity: float = Field(
        default=3.0,
        ge=1.0,
        le=5.0,
        description="How faithfully the code implements the paper's core method.",
    )
    completeness: float = Field(
        default=3.0,
        ge=1.0,
        le=5.0,
        description="Whether all paper method modules have corresponding implementation code.",
    )
    correctness: float = Field(
        default=3.0,
        ge=1.0,
        le=5.0,
        description="Logical correctness: dataflow, formula translation, and module wiring.",
    )
    runnability: float = Field(
        default=3.0,
        ge=1.0,
        le=5.0,
        description="Whether the code includes valid dependencies, entry point, and a smoke test.",
    )
    overall_score: float = Field(
        default=3.0,
        ge=1.0,
        le=5.0,
        description="Mean of paper_fidelity, completeness, correctness, and runnability.",
    )
    detected_problems: list[str] = Field(
        default_factory=list,
        description="Specific problems found in the generated code.",
    )
    revision_suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable suggestions to fix detected problems.",
    )
    verdict: str = Field(
        default="revise",
        description="Overall code quality verdict: 'accept' or 'revise'.",
    )
