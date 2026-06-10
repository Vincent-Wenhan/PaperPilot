"""Environment-based configuration for PaperPilot."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_MOCK_MODE = os.getenv("LLM_MOCK_MODE", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

MAIN_GOAL_DEBUG = "Debug 报错"
