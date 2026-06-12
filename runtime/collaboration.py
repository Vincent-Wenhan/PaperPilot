"""Structured collaboration artifacts exchanged between graph nodes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ReviewIssue(BaseModel):
    source_agent: str
    target_agent: str
    severity: Literal["minor", "important", "critical"]
    issue_type: str
    message: str
    required_action: str
