"""Compute graph node states from workbench events.

Reads events for a run and produces a list of GraphNodeState objects
suitable for the frontend WorkflowGraph component.
"""

from __future__ import annotations

from typing import Any

from backend.schemas import WorkflowStatus


class GraphNodeState:
    """Computed node state for a single graph node."""

    def __init__(
        self,
        id: str,
        label: str,
        agent: str = "",
        status: WorkflowStatus = "pending",
        started_at: str = "",
        finished_at: str = "",
        input_artifacts: list[str] | None = None,
        output_artifacts: list[str] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        issues: list[dict[str, Any]] | None = None,
    ) -> None:
        self.id = id
        self.label = label
        self.agent = agent
        self.status: WorkflowStatus = status
        self.started_at = started_at
        self.finished_at = finished_at
        self.input_artifacts = input_artifacts or []
        self.output_artifacts = output_artifacts or []
        self.tool_calls = tool_calls or []
        self.issues = issues or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "agent": self.agent,
            "status": self.status,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "inputArtifacts": self.input_artifacts,
            "outputArtifacts": self.output_artifacts,
            "toolCalls": self.tool_calls,
            "issues": self.issues,
        }


_REPRODUCE_NODES = [
    ("parse", "Parse Paper", "Research Understanding Agent"),
    ("research_evidence", "Research Evidence", "Research Understanding Agent"),
    ("repo_evidence", "Repository Evidence", "Repository Understanding Agent"),
    ("planning", "Reproduction Planning", "Reproduction Planner Agent"),
    ("command_routing", "Command Routing", "Runner Agent"),
    ("implementation", "Implementation", "Prototype Builder Agent"),
    ("review", "Code Review", "Execution Diagnosis Agent"),
    ("diagnosis", "Diagnosis", "Execution Diagnosis Agent"),
    ("outputs", "Outputs", "Report Builder"),
]

_PRODUCTIZE_NODES = [
    ("parse", "Parse Papers", "Research Synthesizer Agent"),
    ("capability_cards", "Capability Cards", "Research Synthesizer Agent"),
    ("capability_map", "Capability Map", "Research Synthesizer Agent"),
    ("method_composition", "Method Composition", "Research Synthesizer Agent"),
    ("jtbd", "JTBD Analysis", "Product Planner Agent"),
    ("prd", "PRD Generation", "Product Planner Agent"),
    ("mvp", "MVP / MoSCoW", "Product Planner Agent"),
    ("prototype", "Prototype Build", "Prototype Builder Agent"),
    ("evaluation", "Evaluation", "Product Evaluator Agent"),
    ("revision", "Revision Routing", "Product Evaluator Agent"),
    ("scaffold", "Scaffold", "Prototype Builder Agent"),
]

NODE_MAP: dict[str, dict[str, list[tuple[str, str, str]]]] = {
    "reproduce": {"nodes": _REPRODUCE_NODES},
    "productize": {"nodes": _PRODUCTIZE_NODES},
}


class GraphService:
    """Compute graph node states from events."""

    def build_graph(
        self,
        run_mode: str,
        events: list[Any],
    ) -> list[dict[str, Any]]:
        node_defs = NODE_MAP.get(run_mode, NODE_MAP["reproduce"])["nodes"]
        event_by_node: dict[str, list[Any]] = {}
        for evt in events:
            node = getattr(evt, "node", "unknown")
            event_by_node.setdefault(node, []).append(evt)

        nodes: list[dict[str, Any]] = []
        for node_id, label, agent in node_defs:
            node_events = event_by_node.get(node_id, [])
            node_status = self._compute_status(node_events)
            started = ""
            finished = ""
            tool_calls: list[dict[str, Any]] = []
            issues: list[dict[str, Any]] = []
            input_artifacts: list[str] = []
            output_artifacts: list[str] = []

            for evt in node_events:
                created = getattr(evt, "created_at", "")
                etype = getattr(evt, "event_type", "")
                payload = getattr(evt, "payload", {}) or {}

                if etype in ("node_started", "pipeline_started") and not started:
                    started = created
                if etype in ("node_finished", "pipeline_finished") and not finished:
                    finished = created
                if etype in ("tool_call", "tool_result"):
                    tool_calls.append({
                        "eventId": getattr(evt, "event_id", ""),
                        "type": etype,
                        "message": getattr(evt, "message", ""),
                        "payload": payload,
                        "timestamp": created,
                    })
                if etype in ("artifact_created",):
                    name = payload.get("name") or payload.get("path", "")
                    if name:
                        output_artifacts.append(name)
                if etype in ("review_issue", "diagnosis_issue", "evaluation_issue"):
                    issues.append({
                        "eventId": getattr(evt, "event_id", ""),
                        "message": getattr(evt, "message", ""),
                        "payload": payload,
                    })

            nodes.append(
                GraphNodeState(
                    id=node_id,
                    label=label,
                    agent=agent,
                    status=node_status,
                    started_at=started,
                    finished_at=finished,
                    input_artifacts=input_artifacts,
                    output_artifacts=output_artifacts,
                    tool_calls=tool_calls,
                    issues=issues,
                ).to_dict()
            )
        return nodes

    @staticmethod
    def _compute_status(node_events: list[Any]) -> WorkflowStatus:
        if not node_events:
            return "pending"
        has_running = False
        latest_status = "pending"
        for evt in node_events:
            s = getattr(evt, "status", "pending")
            if s == "running":
                has_running = True
            latest_status = s
        if has_running:
            return "running"
        if latest_status in ("success", "failed", "waiting_review", "revised"):
            return latest_status
        return "pending"


graph_service = GraphService()
