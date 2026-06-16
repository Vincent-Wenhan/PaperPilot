"""Productize-mode LangGraph interrupt helpers."""

from __future__ import annotations

from typing import Any

from runtime.checkpointing import build_graph_config

PRODUCTIZE_PROPOSAL_INTERRUPT_AFTER = ("synthesize_research",)
PRODUCTIZE_EXECUTION_INTERRUPT_AFTER = ("build_prototype",)


def invoke_graph(
    graph: Any,
    initial_state: dict[str, Any],
    thread_id: str | None,
) -> dict[str, Any]:
    if thread_id:
        config = build_graph_config(thread_id)
        graph.invoke(initial_state, config)
        snapshot = graph.get_state(config)
        return dict(snapshot.values)
    return dict(graph.invoke(initial_state))


def resume_graph(graph: Any, thread_id: str, action: str = "confirm") -> dict[str, Any]:
    config = build_graph_config(thread_id)
    try:
        from langgraph.types import Command
    except Exception:
        Command = None  # type: ignore[assignment]

    last_error: Exception | None = None
    resume_inputs: list[Any] = []
    if Command is not None:
        resume_inputs.append(Command(resume={"action": action}))
    resume_inputs.extend([None, {}])

    for resume_input in resume_inputs:
        try:
            graph.invoke(resume_input, config)
            snapshot = graph.get_state(config)
            if not snapshot.next:
                return dict(snapshot.values)
        except Exception as exc:
            last_error = exc

    snapshot = graph.get_state(config)
    if snapshot.next and last_error is not None:
        raise last_error
    return dict(snapshot.values)


def graph_is_interrupted(graph: Any, thread_id: str) -> bool:
    snapshot = graph.get_state(build_graph_config(thread_id))
    return bool(snapshot.next)


def get_interrupt_node(graph: Any, thread_id: str) -> str | None:
    snapshot = graph.get_state(build_graph_config(thread_id))
    if not snapshot.next:
        return None
    return str(snapshot.next[0])
