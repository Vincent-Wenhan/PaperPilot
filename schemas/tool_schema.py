"""Schemas for deterministic PaperPilot tool calls."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SafetyLevel = Literal["safe", "review", "sandbox", "blocked"]


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    safety_level: SafetyLevel = "safe"
    allowed_agents: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=30, ge=1, le=600)


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str
    requested_by: str


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    output: Any = None
    error: str = ""
    safety_level: SafetyLevel = "safe"
    elapsed_seconds: float = Field(default=0, ge=0)
