"""Schema for structured paper summary output."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PaperSummary(BaseModel):
    title: Optional[str] = None
    task: str = Field(default="")
    problem: str = Field(default="")
    contributions: List[str] = Field(default_factory=list)
    method_summary: str = Field(default="")
    datasets: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    training_details: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
