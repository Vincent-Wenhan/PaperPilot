"""Schema for structured repository analysis."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class RepoAnalysis(BaseModel):
    framework: str = "unknown"
    task_type: str = "unknown"
    training_entrypoints: List[str] = Field(default_factory=list)
    inference_entrypoints: List[str] = Field(default_factory=list)
    config_files: List[str] = Field(default_factory=list)
    dependency_files: List[str] = Field(default_factory=list)
    dataset_requirements: List[str] = Field(default_factory=list)
    checkpoint_requirements: List[str] = Field(default_factory=list)
    risk_level: str = "medium"
    notes: List[str] = Field(default_factory=list)
