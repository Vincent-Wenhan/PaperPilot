"""Schema for generated Next.js app bundle (strict contract)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GeneratedFile(BaseModel):
    path: str
    content: str
    purpose: str


class AppContract(BaseModel):
    runtime: Literal["nextjs"] = "nextjs"
    package_manager: Literal["npm"] = "npm"
    required_scripts: dict[str, str] = Field(
        default_factory=lambda: {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "test": "vitest run",
        }
    )
    required_routes: list[str]
    required_components: list[str]
    required_api_routes: list[str]
    acceptance_tests: list[str]
    real_adapter_required: bool = True
    mock_fallback_allowed: bool = True


class GeneratedAppBundle(BaseModel):
    contract: AppContract
    files: list[GeneratedFile]
    integration_notes: list[str] = Field(default_factory=list)
