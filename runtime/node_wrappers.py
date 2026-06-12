"""Shared node helpers for graph-based pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pipeline.hitl_context import PipelineHITL
from tools.llm_client import LLMClient


@dataclass(frozen=True)
class ProductizeGraphContext:
    llm_client: LLMClient
    progress_callback: Callable[[str], None] | None = None
    hitl: PipelineHITL | None = None
    output_dir: str | Path = "generated_product"


@dataclass(frozen=True)
class ReproduceGraphContext:
    llm_client: LLMClient
    progress_callback: Callable[[str], None] | None = None
    hitl: PipelineHITL | None = None
    output_dir: Path | None = None
    generate_code: bool = True
    implementation_model: str = ""


def progress(context: Any, stage: str) -> dict[str, list[str]]:
    """Report progress and append a trace update."""
    callback = getattr(context, "progress_callback", None)
    if callback:
        callback(stage)
    return {"graph_trace": [stage]}
