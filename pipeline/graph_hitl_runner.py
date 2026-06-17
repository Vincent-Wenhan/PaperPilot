"""LangGraph interrupt/resume helpers for synchronous HITL."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from runtime.checkpointing import build_graph_config

REPRODUCE_HITL_INTERRUPT_AFTER = (
    "research_understanding",
    "reproduction_planner",
)

INTERRUPT_NODE_TO_STAGE: dict[str, tuple[str, str]] = {
    "research_understanding": ("research", "Paper Summary"),
    "reproduction_planner": ("experiment", "Experiment Plan"),
}


def new_hitl_thread_id() -> str:
    return f"reproduce-{uuid4().hex}"


def graph_is_interrupted(graph: Any, thread_id: str) -> bool:
    snapshot = graph.get_state(build_graph_config(thread_id))
    return bool(snapshot.next)


def get_interrupt_node(graph: Any, thread_id: str) -> str | None:
    snapshot = graph.get_state(build_graph_config(thread_id))
    if not snapshot.next:
        return None
    return str(snapshot.next[0])


def render_interrupt_content(result: dict[str, Any], node_name: str) -> str:
    if node_name == "research_understanding":
        return f"{result.get('paper_info', '')}\n\n{result.get('method_info', '')}".strip()
    if node_name == "reproduction_planner":
        return (
            f"{result.get('env_plan', '')}\n\n{result.get('experiment_plan', '')}".strip()
        )
    return "Review the generated output before continuing."


def invoke_until_pause_or_complete(
    graph: Any,
    initial_state: dict[str, Any],
    thread_id: str | None,
) -> dict[str, Any]:
    if thread_id:
        config = build_graph_config(thread_id)
        graph.invoke(initial_state, config)
        snapshot = graph.get_state(config)
        return dict(snapshot.values)
    state = graph.invoke(initial_state)
    return dict(state)


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
            return dict(snapshot.values)
        except Exception as exc:
            last_error = exc
    snapshot = graph.get_state(config)
    if snapshot.next and last_error is not None:
        raise last_error
    return dict(snapshot.values)
