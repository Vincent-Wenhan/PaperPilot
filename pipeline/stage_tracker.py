"""Track whether each pipeline stage used real LLM output, fallback, or mock."""

from __future__ import annotations

from typing import Any

STAGE_REAL = "real"
STAGE_FALLBACK = "fallback"
STAGE_MOCK = "mock"

STAGE_DISPLAY_NAMES: dict[str, str] = {
    "research": "Paper Summary",
    "repository": "Repository Analysis",
    "experiment": "Experiment Plan",
    "implementation": "Code Generation",
    "diagnosis": "Execution Diagnosis",
    "capabilities": "Capability Cards",
    "prototype": "Prototype Plan",
}

AGENT_STAGE_KEYS: dict[str, str] = {
    "Research Understanding Agent": "research",
    "Research Understanding Agent (retry)": "research",
    "Repository Understanding Agent": "repository",
    "Repository Understanding Agent (retry)": "repository",
    "Reproduction Planner Agent": "experiment",
    "Reproduction Planner Agent (retry)": "experiment",
    "Reproduction Implementation Agent": "implementation",
    "Reproduction Implementation Agent (main model retry)": "implementation",
    "Execution & Diagnosis Agent": "diagnosis",
}


def normalize_agent_stage(stage: str) -> str:
    """Map agent stage labels to stable HITL / UI keys."""
    return AGENT_STAGE_KEYS.get(stage, stage.lower().replace(" ", "_"))


def record_stage_source(
    result: dict[str, Any],
    stage: str,
    source: str,
) -> None:
    """Record provenance for one agent stage."""
    sources = result.setdefault("stage_sources", {})
    key = normalize_agent_stage(stage)
    sources[key] = source


def init_stage_sources(result: dict[str, Any]) -> None:
    """Ensure stage_sources exists on a pipeline result dict."""
    result.setdefault("stage_sources", {})


def stage_badge_label(source: str) -> str:
    """Human-readable badge for a stage source."""
    return {
        STAGE_REAL: "Real LLM",
        STAGE_FALLBACK: "Fallback",
        STAGE_MOCK: "Mock",
    }.get(source, source)
