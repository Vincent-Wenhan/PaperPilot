"""Schema for runner command planning and results."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CommandPlan(BaseModel):
    command: str
    purpose: str = ""
    risk_level: str = "low"
    requires_confirmation: bool = False
    blocked_reason: Optional[str] = None


class AgentBudget(BaseModel):
    max_tool_calls: int = Field(default=8, ge=1)
    max_repair_rounds: int = Field(default=2, ge=0)
    max_revision_rounds: int = Field(default=2, ge=0)
    require_artifact_each_round: bool = True


class CommandResult(BaseModel):
    command: str
    mode: str = "safe"
    executed: bool = False
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    timeout: bool = False
    risk_level: str = "unknown"
    blocked_reason: Optional[str] = None
    sandbox_dir: Optional[str] = None
