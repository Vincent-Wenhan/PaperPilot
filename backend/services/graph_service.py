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
    ("mvp", "Proposal Review", "Product Planner Agent"),
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
        node_order = [node_id for node_id, _label, _agent in node_defs]
        node_index = {node_id: index for index, node_id in enumerate(node_order)}
        event_by_node: dict[str, list[Any]] = {}
        last_mapped_node = ""
        for evt in events:
            node = getattr(evt, "node", "unknown")
            event_by_node.setdefault(node, []).append(evt)
            mapped_node = self._node_from_event(
                run_mode,
                evt,
                last_mapped_node=last_mapped_node,
            )
            if mapped_node and mapped_node != node:
                event_by_node.setdefault(mapped_node, []).append(evt)
            if mapped_node in node_index and str(getattr(evt, "event_type", "") or "") != "pipeline_failed":
                last_mapped_node = mapped_node

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
                if etype in ("node_finished", "pipeline_finished", "review_actions_resolved") and not finished:
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
        self._advance_progression(nodes, node_index, event_by_node)
        return nodes

    @staticmethod
    def _compute_status(node_events: list[Any]) -> WorkflowStatus:
        if not node_events:
            return "pending"
        has_running = False
        latest_status: WorkflowStatus = "pending"
        for evt in node_events:
            s = getattr(evt, "status", "pending")
            if s == "running":
                has_running = True
            latest_status = s
        if latest_status in ("success", "failed", "waiting_review", "revised"):
            return latest_status
        if has_running:
            return "running"
        return "pending"

    @staticmethod
    def _node_from_event(
        run_mode: str,
        event: Any,
        *,
        last_mapped_node: str = "",
    ) -> str:
        """Map runtime events to graph nodes.

        Priority: structured event.node > event_type mapping > message keyword fallback.
        Legacy message matching is preserved for backward compatibility.
        """
        raw_node = str(getattr(event, "node", "") or "")
        event_type = str(getattr(event, "event_type", "") or "")
        payload = getattr(event, "payload", {}) or {}
        pipeline_status = ""
        if isinstance(payload, dict):
            pipeline_status = str(payload.get("pipeline_status", "") or "")

        # Pipeline lifecycle events mapped to terminal nodes
        if raw_node in {"run_intake", "input_review"}:
            return "parse"
        if raw_node == "planner":
            return "planning" if run_mode == "reproduce" else "prd"
        if run_mode == "productize" and event_type == "pipeline_failed":
            return (
                GraphService._productize_error_node(payload)
                or last_mapped_node
                or "parse"
            )
        if run_mode == "productize" and event_type == "pipeline_finished" and pipeline_status == "proposal_review":
            return "mvp"
        if run_mode == "productize" and event_type == "proposal_executed":
            if str(getattr(event, "status", "") or "") == "failed" or pipeline_status == "failed":
                return (
                    GraphService._productize_error_node(payload)
                    or last_mapped_node
                    or "scaffold"
                )
            return "scaffold"
        if event_type in {"pipeline_finished", "pipeline_failed", "review_actions_resolved"}:
            return "outputs" if run_mode == "reproduce" else "scaffold"

        # Legacy keyword-based fallback for messages that don't carry structured node ids
        message = str(getattr(event, "message", "") or "").lower()

        if run_mode == "productize":
            if "extracting capability" in message:
                return "capability_cards"
            if "composing paper capabilities" in message:
                return "capability_map"
            if "inspecting generated product" in message:
                return "scaffold"
            if "capability card" in message:
                return "capability_cards"
            if "capability map" in message:
                return "capability_map"
            if "composition" in message:
                return "method_composition"
            if "jtbd" in message or "job-to-be-done" in message:
                return "jtbd"
            if "prd" in message:
                return "prd"
            if "mvp" in message or "moscow" in message:
                return "mvp"
            if "evaluation" in message or "evaluator" in message:
                return "evaluation"
            if "scaffold" in message:
                return "scaffold"
            if "selecting product template" in message:
                return "prototype"
            if "prototype" in message:
                return "prototype"
            if "revision" in message:
                return "revision"

        # Structured node mapping: if event.node matches a known node id, use it directly
        known_nodes = {nid for nid, _label, _agent in NODE_MAP.get(run_mode, NODE_MAP["reproduce"])["nodes"]}
        if raw_node in known_nodes:
            return raw_node

        if "research understanding" in message:
            return "research_evidence"
        if "repository cloner" in message or "repository understanding" in message:
            return "repo_evidence"
        if "reproduction planner" in message:
            return "planning"
        if "command" in message and ("routing" in message or "review" in message):
            return "command_routing"
        if "implementation agent" in message or "generating code" in message or "revising code" in message:
            return "implementation"
        if "sandbox" in message:
            return "command_routing"
        if "code review" in message or "second review" in message or "review verdict" in message:
            return "review"
        if "execution" in message or "diagnosis" in message:
            return "diagnosis"
        if "report" in message or "output" in message:
            return "outputs"
        return raw_node

    @staticmethod
    def _productize_error_node(payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""
        errors = payload.get("errors")
        if not isinstance(errors, list):
            return ""
        text = " ".join(str(error).lower() for error in errors)
        if "prototype builder agent" in text:
            return "prototype"
        if "product evaluator agent" in text:
            return "evaluation"
        if "product planner agent" in text:
            return "prd"
        if "research synthesizer agent" in text:
            return "capability_cards"
        if "scaffold" in text:
            return "scaffold"
        return ""

    @staticmethod
    def _advance_progression(
        nodes: list[dict[str, Any]],
        node_index: dict[str, int],
        event_by_node: dict[str, list[Any]],
    ) -> None:
        active_indices = [
            node_index[node_id]
            for node_id in event_by_node
            if node_id in node_index and event_by_node[node_id]
        ]
        if not active_indices:
            return

        finished_events = [
            evt
            for node_events in event_by_node.values()
            for evt in node_events
            if str(getattr(evt, "event_type", "") or "") in {
                "pipeline_finished",
                "pipeline_failed",
                "review_actions_resolved",
                "proposal_executed",
            }
        ]
        if finished_events:
            final_status = str(getattr(finished_events[-1], "status", "success") or "success")
            terminal_indices = [
                node_index[node_id]
                for node_id, node_events in event_by_node.items()
                if node_id in node_index
                and any(
                    str(getattr(evt, "event_type", "") or "") in {
                        "pipeline_finished",
                        "pipeline_failed",
                        "review_actions_resolved",
                        "proposal_executed",
                    }
                    for evt in node_events
                )
            ]
            final_index = max(terminal_indices) if terminal_indices else max(active_indices)
            for index, node in enumerate(nodes):
                if index < final_index and node["status"] in {"pending", "running", "waiting_review"}:
                    node["status"] = "success"
                elif index == final_index:
                    node["status"] = final_status
                elif final_status == "failed" and node["status"] in {"running", "waiting_review"}:
                    node["status"] = "pending"
            return

        latest_index = max(active_indices)
        for index, node in enumerate(nodes):
            if index < latest_index and node["status"] in {"pending", "running", "waiting_review"}:
                node["status"] = "success"
            elif index == latest_index and node["status"] == "pending":
                node["status"] = "running"


graph_service = GraphService()
