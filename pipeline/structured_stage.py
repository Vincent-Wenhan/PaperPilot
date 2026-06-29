"""Shared helpers for the Reproduce and Productize pipelines.

Both pipelines duplicated the same ``_run_structured_stage`` and
``_llm_client_key`` helpers. This module is the single source of truth so
bug fixes only need to land once.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from pipeline.stage_tracker import (
    STAGE_FALLBACK,
    STAGE_MOCK,
    STAGE_REAL,
    record_stage_source,
)
from tools.llm_client import LLMClient, LLMClientError

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def llm_client_key(client: LLMClient) -> str:
    """Return a stable cache key for an LLM client."""
    return f"{getattr(client, 'base_url', '')}|{getattr(client, 'model', '')}"


def record_stage_error(result: dict[str, Any], step: str, error: object) -> None:
    """Append a stage-tagged error to ``result['errors']``."""
    result["errors"].append(f"[{step}] {error}")


def run_structured_stage(
    result: dict[str, Any],
    stage: str,
    agent_factory: Callable[[LLMClient], Any],
    llm_client: LLMClient,
    input_data: dict[str, Any],
    fallback: Callable[[], SchemaT],
    *,
    record_sources: bool = True,
) -> SchemaT:
    """Run a structured agent stage with fallback and stage-source tracking.

    - If the client is marked unavailable in ``result['llm_unavailable_clients']``
      and is not in mock mode, immediately invoke the fallback.
    - If the client is in mock mode, record the stage as mock and invoke the
      fallback.
    - Otherwise, increment ``llm_attempts`` and try the agent. On
      ``LLMClientError`` that blocks the client, mark the client as
      unavailable so later stages skip straight to the fallback.
    - Any other exception is recorded as an error and the fallback is used.
    """
    client_key = llm_client_key(llm_client)
    unavailable_clients = result["llm_unavailable_clients"]
    if client_key in unavailable_clients and not llm_client.mock_mode:
        if record_sources:
            record_stage_source(result, stage, STAGE_FALLBACK)
        return fallback()
    if llm_client.mock_mode:
        if record_sources:
            record_stage_source(result, stage, STAGE_MOCK)
        return fallback()
    result["llm_attempts"] += 1
    try:
        output = agent_factory(llm_client).run_structured(input_data)
        if record_sources:
            record_stage_source(result, stage, STAGE_REAL)
        return output
    except LLMClientError as exc:
        result["llm_failures"] += 1
        if exc.blocks_client and client_key not in unavailable_clients:
            unavailable_clients.append(client_key)
        fallback_note = (
            "Remaining stages using the same endpoint and model used fallback outputs."
            if exc.blocks_client
            else "This stage used a fallback output; later stages will continue."
        )
        record_stage_error(result, stage, f"{exc} {fallback_note}")
        if record_sources:
            record_stage_source(result, stage, STAGE_FALLBACK)
        return fallback()
    except Exception as exc:
        record_stage_error(result, stage, exc)
        if record_sources:
            record_stage_source(result, stage, STAGE_FALLBACK)
        return fallback()
