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


def resume_graph(graph: Any, thread_id: str) -> dict[str, Any]:
    config = build_graph_config(thread_id)
    graph.invoke(None, config)
    snapshot = graph.get_state(config)
    return dict(snapshot.values)


def graph_is_interrupted(graph: Any, thread_id: str) -> bool:
    snapshot = graph.get_state(build_graph_config(thread_id))
    return bool(snapshot.next)


def get_interrupt_node(graph: Any, thread_id: str) -> str | None:
    snapshot = graph.get_state(build_graph_config(thread_id))
    if not snapshot.next:
        return None
    return str(snapshot.next[0])
