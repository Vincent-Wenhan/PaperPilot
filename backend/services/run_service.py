"""In-memory run and approval state for the workbench API facade."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from backend.schemas import (
    ActionEditRequest,
    ActionRequest,
    RunCreateRequest,
    RunRecord,
    WorkbenchEvent,
)
from backend.services.workbench_mock import (
    build_mock_run,
    build_mock_actions,
    build_mock_events,
    utc_now,
)


REPRODUCE_PLAN = [
    "Parse paper and extract resource links",
    "Build structured research understanding",
    "Scan repository entrypoints and dependencies",
    "Generate reproduction plan and command route",
    "Review bounded command before execution",
    "Diagnose execution result and write report",
]

PRODUCTIZE_PLAN = [
    "Parse papers and normalize capability cards",
    "Build capability map and method composition",
    "Generate PRD, MVP, and MoSCoW scope",
    "Build mock-first prototype plan",
    "Evaluate product faithfulness and demo readiness",
    "Scaffold generated_product and inspect files",
]


class InMemoryRunService:
    """Small state store for local workbench development.

    This is intentionally not a durable run database. The public methods form
    the API boundary that can later delegate to LangGraph checkpointers or a
    persistent store.
    """

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._events: dict[str, list[WorkbenchEvent]] = {}
        self._actions: dict[str, list[ActionRequest]] = {}
        self.seed_mock_run()

    def seed_mock_run(self) -> RunRecord:
        """Register the mock workbench run so action endpoints can mutate it."""
        run = build_mock_run()
        self._runs[run.run_id] = run
        self._events[run.run_id] = build_mock_events(run.run_id)
        self._actions[run.run_id] = build_mock_actions(run.run_id)
        return deepcopy(run)

    def create_run(self, request: RunCreateRequest) -> RunRecord:
        run_id = f"run_{uuid4().hex[:12]}"
        now = utc_now()
        plan = REPRODUCE_PLAN if request.mode == "reproduce" else PRODUCTIZE_PLAN
        inputs = {
            "pdf_path": request.pdf_path,
            "github_url": request.github_url,
            "target_user": request.target_user,
            "product_goal": request.product_goal,
        }
        summary = (
            "Reproduce workflow planned and waiting for runner approval."
            if request.mode == "reproduce"
            else "Productize workflow planned with mock-first scaffold review."
        )
        run = RunRecord(
            run_id=run_id,
            project_id=request.project_id,
            mode=request.mode,
            status="waiting_review",
            task=request.task,
            created_at=now,
            updated_at=now,
            summary=summary,
            inputs=inputs,
            plan=plan,
        )
        self._runs[run_id] = run
        self._events[run_id] = self._build_run_events(run)
        self._actions[run_id] = [
            action.model_copy(update={"run_id": run_id})
            for action in build_mock_actions(run_id)
        ]
        return deepcopy(run)

    def _build_run_events(self, run: RunRecord) -> list[WorkbenchEvent]:
        """Create input-aware run events for newly submitted workbench runs."""
        paper = run.inputs.get("pdf_path") or "paper input"
        repo = run.inputs.get("github_url") or "repository input"
        task = run.task or "No task provided"
        now = utc_now()
        return [
            WorkbenchEvent(
                event_id=f"evt_{uuid4().hex[:10]}",
                run_id=run.run_id,
                node="run_intake",
                agent="Workbench",
                event_type="run_created",
                status="success",
                message=f"Created {run.mode} run for project {run.project_id}.",
                payload={"inputs": run.inputs},
                created_at=now,
            ),
            WorkbenchEvent(
                event_id=f"evt_{uuid4().hex[:10]}",
                run_id=run.run_id,
                node="input_review",
                agent="Input Router",
                event_type="input_received",
                status="running",
                message=f"Received paper: {paper}; repository: {repo}.",
                payload={"paper": paper, "repository": repo},
                created_at=now,
            ),
            WorkbenchEvent(
                event_id=f"evt_{uuid4().hex[:10]}",
                run_id=run.run_id,
                node="planner",
                agent="Planning Agent",
                event_type="plan_generated",
                status="waiting_review",
                message=f"Generated editable plan for task: {task}",
                payload={"plan": run.plan},
                created_at=now,
            ),
        ]

    def get_run(self, run_id: str) -> RunRecord | None:
        run = self._runs.get(run_id)
        return deepcopy(run) if run else None

    def list_events(self, run_id: str) -> list[WorkbenchEvent]:
        return deepcopy(self._events.get(run_id, []))

    def list_actions(self, run_id: str) -> list[ActionRequest]:
        return deepcopy(self._actions.get(run_id, []))

    def get_action(self, action_id: str) -> ActionRequest | None:
        for actions in self._actions.values():
            for action in actions:
                if action.action_id == action_id:
                    return deepcopy(action)
        return None

    def approve_action(self, action_id: str) -> ActionRequest | None:
        return self._update_action_status(action_id, "approved")

    def reject_action(self, action_id: str) -> ActionRequest | None:
        return self._update_action_status(action_id, "rejected")

    def edit_action(
        self,
        action_id: str,
        request: ActionEditRequest,
    ) -> ActionRequest | None:
        for actions in self._actions.values():
            for index, action in enumerate(actions):
                if action.action_id == action_id:
                    updated = action.model_copy(
                        update={
                            "status": "edited",
                            "edited_command": request.edited_command,
                            "reason": request.reason or action.reason,
                        }
                    )
                    actions[index] = updated
                    return deepcopy(updated)
        return None

    def _update_action_status(
        self,
        action_id: str,
        status: str,
    ) -> ActionRequest | None:
        for actions in self._actions.values():
            for index, action in enumerate(actions):
                if action.action_id == action_id:
                    updated = action.model_copy(update={"status": status})
                    actions[index] = updated
                    return deepcopy(updated)
        return None


run_service = InMemoryRunService()
