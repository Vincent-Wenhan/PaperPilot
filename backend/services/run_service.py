"""In-memory run, approval, and agent execution state for the workbench API."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from backend.schemas import (
    ActionEditRequest,
    ActionRequest,
    RunCreateRequest,
    RunRecord,
    WorkbenchEvent,
)
from backend.services.event_service import event_service
from backend.services.workbench_mock import (
    build_mock_actions,
    build_mock_events,
    build_mock_run,
    utc_now,
)
from tools.llm_client import LLMClient


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

    The workbench keeps state in memory for now, but it calls the same
    PaperPilot pipeline functions that power the Streamlit UI.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._runs: dict[str, RunRecord] = {}
        self._events: dict[str, list[WorkbenchEvent]] = {}
        self._actions: dict[str, list[ActionRequest]] = {}
        self._results: dict[str, dict[str, Any]] = {}
        self.seed_mock_run()

    def seed_mock_run(self) -> RunRecord:
        """Register the mock workbench run so action endpoints can mutate it."""
        run = build_mock_run()
        with self._lock:
            self._runs[run.run_id] = run
            self._events[run.run_id] = build_mock_events(run.run_id)
            self._actions[run.run_id] = build_mock_actions(run.run_id)
        return deepcopy(run)

    def create_run(
        self,
        request: RunCreateRequest,
        *,
        start_pipeline: bool = False,
    ) -> RunRecord:
        run_id = f"run_{uuid4().hex[:12]}"
        now = utc_now()
        plan = REPRODUCE_PLAN if request.mode == "reproduce" else PRODUCTIZE_PLAN
        summary = (
            (
                "Reproduce agent workflow is running."
                if request.mode == "reproduce"
                else "Productize agent workflow is running."
            )
            if start_pipeline
            else (
                "Reproduce workflow planned and waiting for runner approval."
                if request.mode == "reproduce"
                else "Productize workflow planned with mock-first scaffold review."
            )
        )
        run = RunRecord(
            run_id=run_id,
            project_id=request.project_id,
            mode=request.mode,
            status="running" if start_pipeline else "waiting_review",
            task=request.task,
            created_at=now,
            updated_at=now,
            summary=summary,
            inputs=self._inputs_from_request(request),
            plan=plan,
        )
        with self._lock:
            self._runs[run_id] = run
            self._events[run_id] = self._build_run_events(run)
            self._actions[run_id] = [
                action.model_copy(
                    update={
                        "action_id": f"act_{run_id}_smoke_test",
                        "run_id": run_id,
                    }
                )
                for action in build_mock_actions(run_id)
            ]
        if start_pipeline:
            self._executor.submit(self.run_pipeline_now, run_id, request)
        return deepcopy(run)

    @staticmethod
    def _effective_mock_mode(request: RunCreateRequest) -> bool:
        return request.mock_mode

    def _inputs_from_request(self, request: RunCreateRequest) -> dict[str, str]:
        return {
            "pdf_path": request.pdf_path,
            "github_url": request.github_url,
            "hardware": request.hardware,
            "gpu_info": request.gpu_info,
            "goal": request.goal,
            "target_user": request.target_user,
            "product_goal": request.product_goal,
            "preferred_type": request.preferred_type,
            "llm_base_url": request.base_url,
            "llm_model": request.model,
            "implementation_model": request.implementation_model,
            "mock_mode": str(self._effective_mock_mode(request)),
        }

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
        with self._lock:
            run = self._runs.get(run_id)
        return deepcopy(run) if run else None

    def list_events(self, run_id: str) -> list[WorkbenchEvent]:
        with self._lock:
            return deepcopy(self._events.get(run_id, []))

    def list_actions(self, run_id: str) -> list[ActionRequest]:
        with self._lock:
            return deepcopy(self._actions.get(run_id, []))

    def get_result(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            result = self._results.get(run_id)
        return deepcopy(result) if result is not None else None

    def get_action(self, action_id: str) -> ActionRequest | None:
        with self._lock:
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
        with self._lock:
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

    def run_pipeline_now(
        self,
        run_id: str,
        request: RunCreateRequest,
    ) -> RunRecord | None:
        """Run the selected PaperPilot pipeline and persist status/events."""
        if self.get_run(run_id) is None:
            return None
        self._append_event(
            run_id,
            node="agent_runtime",
            agent="Workbench Runner",
            event_type="pipeline_started",
            status="running",
            message="Starting PaperPilot agent pipeline.",
        )
        try:
            result = self._execute_pipeline(run_id, request)
        except Exception as exc:
            message = str(exc) or type(exc).__name__
            result_summary = {"pipeline_status": "failed", "errors": [message]}
            self._store_result(run_id, result_summary)
            self._append_event(
                run_id,
                node="agent_runtime",
                agent="Workbench Runner",
                event_type="pipeline_failed",
                status="failed",
                message=f"Agent pipeline failed: {message}",
                payload=result_summary,
            )
            return self._update_run_status(
                run_id,
                status="failed",
                summary=f"Agent pipeline failed: {message}",
                result_summary=result_summary,
            )

        result_summary = self._summarize_result(result)
        pipeline_status = str(result.get("pipeline_status") or "complete")
        status = self._status_from_pipeline(pipeline_status)
        summary = self._summary_from_result(request, result_summary, status)
        self._store_result(run_id, result)
        self._append_event(
            run_id,
            node="agent_runtime",
            agent="Workbench Runner",
            event_type="pipeline_finished",
            status=status,
            message=summary,
            payload=result_summary,
        )
        return self._update_run_status(
            run_id,
            status=status,
            summary=summary,
            result_summary=result_summary,
        )

    def _execute_pipeline(
        self,
        run_id: str,
        request: RunCreateRequest,
    ) -> dict[str, Any]:
        pdf_path = Path(request.pdf_path).expanduser()
        if not request.pdf_path.strip():
            raise ValueError(
                "A local PDF path is required before the Workbench can run agents."
            )
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        client = LLMClient(
            api_key=request.api_key or None,
            base_url=request.base_url or None,
            model=request.model or None,
            mock_mode=self._effective_mock_mode(request),
        )

        def progress(stage: str) -> None:
            self._append_event(
                run_id,
                node="agent_progress",
                agent="PaperPilot Agent",
                event_type="agent_progress",
                status="running",
                message=stage,
            )

        if request.mode == "productize":
            return self._execute_productize(pdf_path, request, client, progress)
        return self._execute_reproduce(pdf_path, request, client, progress)

    @staticmethod
    def _execute_reproduce(
        pdf_path: Path,
        request: RunCreateRequest,
        client: LLMClient,
        progress: Any,
    ) -> dict[str, Any]:
        from main import run_paperpilot

        generate_code = request.goal != "understand paper"

        return run_paperpilot(
            pdf_path=str(pdf_path),
            github_url=request.github_url.strip(),
            hardware=request.hardware,
            gpu_info=request.gpu_info.strip(),
            goal=request.goal,
            llm_client=client,
            progress_callback=progress,
            user_idea=request.task.strip(),
            paper_name=pdf_path.stem.replace(" ", "_")[:80],
            generate_code=generate_code,
            implementation_model=request.implementation_model.strip(),
        )

    def _execute_productize(
        self,
        pdf_path: Path,
        request: RunCreateRequest,
        client: LLMClient,
        progress: Any,
    ) -> dict[str, Any]:
        from main import run_paperpilot
        from pipeline.productize_pipeline import run_productize_pipeline

        progress("Analyzing paper before Productize pipeline")
        analysis = run_paperpilot(
            pdf_path=str(pdf_path),
            github_url=request.github_url.strip(),
            hardware=request.hardware,
            gpu_info=request.gpu_info.strip(),
            goal="run official demo",
            llm_client=client,
            progress_callback=progress,
            user_idea=request.task.strip(),
            paper_name=pdf_path.stem.replace(" ", "_")[:80],
            generate_code=False,
        )
        paper = {
            "paper_id": "paper-1",
            "title": pdf_path.stem,
            "paper_info": analysis.get("paper_info", ""),
            "method_info": analysis.get("method_info", ""),
            "repo_info": analysis.get("repo_info", ""),
            "repo_path": analysis.get("repo_path", ""),
            "repo_source": analysis.get("repo_source", ""),
            "errors": analysis.get("errors", []),
        }
        result = run_productize_pipeline(
            paper_info=paper["paper_info"],
            method_info=paper["method_info"],
            repo_info=paper["repo_info"],
            repo_path=paper["repo_path"],
            target_user=request.target_user.strip() or "PaperPilot users",
            product_goal=request.product_goal.strip() or request.task.strip(),
            llm_client=client,
            preferred_type=request.preferred_type or "auto",
            progress_callback=progress,
            user_idea=request.task.strip(),
            papers=[paper],
        )
        result["source_analysis"] = self._summarize_result(analysis)
        return result

    def _append_event(
        self,
        run_id: str,
        *,
        node: str,
        agent: str,
        event_type: str,
        status: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = WorkbenchEvent(
            event_id=f"evt_{uuid4().hex[:10]}",
            run_id=run_id,
            node=node,
            agent=agent,
            event_type=event_type,
            status=status,
            message=message,
            payload=payload or {},
            created_at=utc_now(),
        )
        with self._lock:
            self._events.setdefault(run_id, []).append(event)
        event_service.emit(event)

    def _update_run_status(
        self,
        run_id: str,
        *,
        status: str,
        summary: str,
        result_summary: dict[str, Any] | None = None,
    ) -> RunRecord | None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            updated = run.model_copy(
                update={
                    "status": status,
                    "summary": summary,
                    "updated_at": utc_now(),
                    "result_summary": result_summary or run.result_summary,
                }
            )
            self._runs[run_id] = updated
            return deepcopy(updated)

    def _store_result(self, run_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            self._results[run_id] = deepcopy(result)

    @staticmethod
    def _status_from_pipeline(pipeline_status: str) -> str:
        if pipeline_status == "failed":
            return "failed"
        if pipeline_status in {"degraded", "hitl_paused"}:
            return "waiting_review"
        return "success"

    @staticmethod
    def _summarize_result(result: dict[str, Any]) -> dict[str, Any]:
        errors = result.get("errors") or []
        scaffold = result.get("scaffold_result") or {}
        return {
            "pipeline_status": str(result.get("pipeline_status") or "complete"),
            "errors": list(errors[:5]) if isinstance(errors, list) else [str(errors)],
            "llm_attempts": int(result.get("llm_attempts") or 0),
            "llm_failures": int(result.get("llm_failures") or 0),
            "report_ready": bool(result.get("report")),
            "run_script_ready": bool(result.get("run_sh")),
            "generated_files": len(result.get("generated_files") or []),
            "product_output_dir": str(scaffold.get("output_dir") or ""),
        }

    @staticmethod
    def _summary_from_result(
        request: RunCreateRequest,
        result_summary: dict[str, Any],
        status: str,
    ) -> str:
        pipeline_status = result_summary.get("pipeline_status", "complete")
        if status == "failed":
            return f"{request.mode} agent pipeline failed."
        if status == "waiting_review":
            return f"{request.mode} agent pipeline completed with review items."
        return f"{request.mode} agent pipeline completed ({pipeline_status})."

    def _update_action_status(
        self,
        action_id: str,
        status: str,
    ) -> ActionRequest | None:
        with self._lock:
            for actions in self._actions.values():
                for index, action in enumerate(actions):
                    if action.action_id == action_id:
                        updated = action.model_copy(update={"status": status})
                        actions[index] = updated
                        return deepcopy(updated)
        return None


run_service = InMemoryRunService()
