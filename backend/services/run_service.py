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
    ActionExecutionResult,
    ActionRequest,
    CommandRunResult,
    CommandRunRequest,
    PatchApplyResult,
    PatchProposeRequest,
    RunCreateRequest,
    RunRecord,
    WorkbenchEvent,
)
from backend.services.command_service import command_service
from backend.services.event_service import event_service
from backend.services.patch_service import patch_service
from backend.services.workbench_mock import (
    build_mock_actions,
    build_mock_events,
    build_mock_run,
    utc_now,
)
from config import PROJECT_ROOT
from tools.command_runner import plan_command
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
            self._actions[run_id] = []
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
        action = self._update_action_status(action_id, "rejected")
        if action is not None:
            self._append_event(
                action.run_id,
                node="runner_review",
                agent="Workbench",
                event_type="action_rejected",
                status="failed",
                message=f"Rejected action {action.action_id}.",
                payload={"action_id": action.action_id, "tool": action.tool},
            )
        return action

    def edit_action(
        self,
        action_id: str,
        request: ActionEditRequest,
    ) -> ActionRequest | None:
        with self._lock:
            for actions in self._actions.values():
                for index, action in enumerate(actions):
                    if action.action_id == action_id:
                        if action.tool != "run_command":
                            raise ValueError("Only command actions can be edited.")
                        if action.execution_status != "not_started":
                            raise ValueError("Executed actions cannot be edited.")
                        if action.status == "rejected":
                            raise ValueError("Rejected actions cannot be edited.")
                        updated = action.model_copy(
                            update={
                                "status": "edited",
                                "edited_command": request.edited_command,
                                "reason": request.reason or action.reason,
                            }
                        )
                        actions[index] = updated
                        result = deepcopy(updated)
                        break
                else:
                    continue
                break
            else:
                return None
        self._append_event(
            result.run_id,
            node="runner_review",
            agent="Workbench",
            event_type="action_edited",
            status="waiting_review",
            message=f"Edited action {result.action_id}; execution still requires approval.",
            payload={"action_id": result.action_id, "tool": result.tool},
        )
        return result

    def execute_action(self, action_id: str) -> ActionExecutionResult | None:
        with self._lock:
            located = self._locate_action_locked(action_id)
            if located is None:
                return None
            _, index, action = located
            if action.execution_status in {"succeeded", "failed", "blocked"}:
                return self._execution_response_from_action(action)
            if action.execution_status == "running":
                return self._execution_response_from_action(action)
            if action.status == "rejected":
                raise ValueError("Rejected actions cannot execute.")
            if action.status not in {"pending", "edited"}:
                raise ValueError("Only pending or edited actions can execute.")
            if action.tool == "run_command" and not self._action_command(action):
                raise ValueError("Command action is missing a command.")
            if action.tool == "apply_patch" and not action.patch_id:
                raise ValueError("Patch action is missing a patch id.")
            updated = action.model_copy(
                update={
                    "status": "approved",
                    "execution_status": "running",
                    "execution_result": {},
                }
            )
            self._actions[updated.run_id][index] = updated

        self._append_event(
            updated.run_id,
            node="runner_review",
            agent="Workbench",
            event_type="action_approved",
            status="success",
            message=f"Approved action {updated.action_id}.",
            payload={"action_id": updated.action_id, "tool": updated.tool},
        )
        self._append_event(
            updated.run_id,
            node="runner_execution",
            agent="Workbench Runner",
            event_type="action_execution_started",
            status="running",
            message=f"Executing {updated.tool} action {updated.action_id}.",
            payload={"action_id": updated.action_id, "tool": updated.tool},
        )

        if updated.tool == "apply_patch":
            return self._execute_patch_action(updated)
        return self._execute_command_action(updated)

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
        actions = self._create_actions_from_result(run_id, result, request)
        if actions:
            result_summary["pending_actions"] = len(actions)
            if status == "success":
                status = "waiting_review"
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

    def _execute_command_action(self, action: ActionRequest) -> ActionExecutionResult:
        command = self._action_command(action)
        try:
            result = command_service.run_command(
                action.run_id,
                CommandRunRequest(
                    command=command,
                    cwd=action.cwd or ".",
                    mode=action.execution_mode,
                ),
            )
        except (FileNotFoundError, PermissionError, ValueError) as exc:
            message = str(exc) or type(exc).__name__
            return self._record_action_execution(
                action.action_id,
                execution_status="failed",
                message=f"Command validation failed: {message}",
                result={"error": message},
            )

        if result.blocked_reason:
            return self._record_action_execution(
                action.action_id,
                execution_status="blocked",
                message=f"Command was blocked by policy: {result.blocked_reason}",
                result=result.model_dump(mode="json"),
                command_result=result,
                blocked_reason=result.blocked_reason,
            )

        success = bool(result.executed and result.exit_code == 0)
        return self._record_action_execution(
            action.action_id,
            execution_status="succeeded" if success else "failed",
            message=(
                "Command completed successfully."
                if success
                else "Command execution finished with a failure result."
            ),
            result=result.model_dump(mode="json"),
            command_result=result,
        )

    def _execute_patch_action(self, action: ActionRequest) -> ActionExecutionResult:
        try:
            result = patch_service.apply_patch(action.patch_id)
        except (FileNotFoundError, PermissionError, ValueError) as exc:
            message = str(exc) or type(exc).__name__
            return self._record_action_execution(
                action.action_id,
                execution_status="failed",
                message=f"Patch validation failed: {message}",
                result={"error": message},
            )
        if result is None:
            return self._record_action_execution(
                action.action_id,
                execution_status="failed",
                message=f"Patch proposal not found: {action.patch_id}",
                result={"patch_id": action.patch_id, "applied": False},
            )

        return self._record_action_execution(
            action.action_id,
            execution_status="succeeded" if result.applied else "failed",
            message=result.message,
            result=result.model_dump(mode="json"),
            patch_result=result,
        )

    def _record_action_execution(
        self,
        action_id: str,
        *,
        execution_status: str,
        message: str,
        result: dict[str, Any],
        command_result: CommandRunResult | None = None,
        patch_result: PatchApplyResult | None = None,
        blocked_reason: str | None = None,
    ) -> ActionExecutionResult:
        with self._lock:
            located = self._locate_action_locked(action_id)
            if located is None:
                raise ValueError("Action not found while recording execution.")
            _, index, action = located
            updated = action.model_copy(
                update={
                    "execution_status": execution_status,
                    "execution_result": result,
                }
            )
            self._actions[updated.run_id][index] = updated
            response = ActionExecutionResult(
                action=deepcopy(updated),
                message=message,
                execution_status=execution_status,
                command_result=command_result,
                patch_result=patch_result,
                blocked_reason=blocked_reason,
            )

        if execution_status == "blocked":
            event_type = "action_policy_blocked"
            event_status = "failed"
        elif execution_status == "succeeded":
            event_type = "action_execution_succeeded"
            event_status = "success"
        else:
            event_type = "action_execution_failed"
            event_status = "failed"
        self._append_event(
            updated.run_id,
            node="runner_execution",
            agent="Workbench Runner",
            event_type=event_type,
            status=event_status,
            message=message,
            payload={
                "action_id": updated.action_id,
                "tool": updated.tool,
                "execution_status": execution_status,
                "result": result,
            },
        )
        return response

    def _execution_response_from_action(
        self,
        action: ActionRequest,
    ) -> ActionExecutionResult:
        command_result = None
        patch_result = None
        if action.execution_result:
            if action.tool == "run_command":
                try:
                    command_result = CommandRunResult.model_validate(
                        action.execution_result
                    )
                except ValueError:
                    command_result = None
            elif action.tool == "apply_patch":
                try:
                    patch_result = PatchApplyResult.model_validate(
                        action.execution_result
                    )
                except ValueError:
                    patch_result = None
        message = (
            "Action execution is already recorded."
            if action.execution_status != "running"
            else "Action execution is already in progress."
        )
        return ActionExecutionResult(
            action=deepcopy(action),
            message=message,
            execution_status=action.execution_status,
            command_result=command_result,
            patch_result=patch_result,
            blocked_reason=(
                str(action.execution_result.get("blocked_reason"))
                if action.execution_result.get("blocked_reason")
                else None
            ),
        )

    def _create_actions_from_result(
        self,
        run_id: str,
        result: dict[str, Any],
        request: RunCreateRequest,
    ) -> list[ActionRequest]:
        actions: list[ActionRequest] = []
        command_action = self._command_action_from_result(run_id, result, request)
        if command_action is not None:
            actions.append(command_action)
        actions.extend(self._patch_actions_from_result(run_id, result))
        if not actions:
            return []

        with self._lock:
            if self._actions.get(run_id):
                return []
            self._actions[run_id] = deepcopy(actions)

        for action in actions:
            self._append_event(
                run_id,
                node="runner_review",
                agent=action.agent,
                event_type="human_review_required",
                status="waiting_review",
                message=f"Action {action.action_id} requires review: {action.reason}",
                payload=action.model_dump(mode="json"),
            )
        return actions

    def _command_action_from_result(
        self,
        run_id: str,
        result: dict[str, Any],
        request: RunCreateRequest,
    ) -> ActionRequest | None:
        command = ""
        reason = ""
        bundle = result.get("implementation_bundle")
        if isinstance(bundle, dict):
            command = str(bundle.get("smoke_test_command") or "").strip()
            if command:
                reason = "Run the generated implementation smoke test from pipeline output."

        if not command:
            for raw_plan in result.get("command_plans") or []:
                if not isinstance(raw_plan, dict):
                    continue
                candidate = str(raw_plan.get("command") or "").strip()
                if candidate:
                    command = candidate
                    reason = str(
                        raw_plan.get("purpose")
                        or "Review the concrete command proposed by the reproduction plan."
                    )
                    break

        if not command:
            command = self._first_run_script_command(str(result.get("run_sh") or ""))
            if command:
                reason = "Review the first concrete command from generated run.sh."

        if not command:
            return None

        plan = plan_command(command)
        risk = str(plan.risk_level or "medium").lower()
        if risk not in {"low", "medium", "high", "blocked"}:
            risk = "medium"
        cwd = self._display_cwd(
            str(
                result.get("generated_repo_path")
                or result.get("repo_path")
                or "."
            )
        )
        execution_mode = "safe" if risk == "low" else "review"
        if not reason:
            reason = plan.blocked_reason or "Review command before execution."
        return ActionRequest(
            action_id=f"act_{uuid4().hex[:12]}",
            run_id=run_id,
            agent="Reproduction Planner Agent",
            tool="run_command",
            command=command,
            cwd=cwd,
            execution_mode=execution_mode,
            risk=risk,  # type: ignore[arg-type]
            reason=reason,
        )

    def _patch_actions_from_result(
        self,
        run_id: str,
        result: dict[str, Any],
    ) -> list[ActionRequest]:
        raw_specs: list[Any] = []
        if result.get("patch_id"):
            raw_specs.append(result)
        if isinstance(result.get("patch_proposal"), dict):
            raw_specs.append(result["patch_proposal"])
        if isinstance(result.get("patch_proposals"), list):
            raw_specs.extend(result["patch_proposals"])

        actions: list[ActionRequest] = []
        for spec in raw_specs:
            if not isinstance(spec, dict):
                continue
            patch_id = str(spec.get("patch_id") or "").strip()
            patch = patch_service.get_patch(patch_id) if patch_id else None
            if patch is None and spec.get("path") and "new_content" in spec:
                patch = patch_service.propose_patch(
                    run_id,
                    PatchProposeRequest(
                        path=str(spec["path"]),
                        new_content=str(spec.get("new_content") or ""),
                        reason=str(spec.get("reason") or ""),
                    ),
                )
            if patch is None:
                continue
            actions.append(
                ActionRequest(
                    action_id=f"act_{uuid4().hex[:12]}",
                    run_id=run_id,
                    agent=str(spec.get("agent") or "Prototype Builder Agent"),
                    tool="apply_patch",
                    patch_id=patch.patch_id,
                    path=patch.path,
                    risk="medium",
                    reason=str(
                        spec.get("reason")
                        or patch.reason
                        or "Apply generated patch proposal."
                    ),
                )
            )
        return actions

    @staticmethod
    def _action_command(action: ActionRequest) -> str:
        if action.status == "edited" and action.edited_command.strip():
            return action.edited_command.strip()
        return action.command.strip()

    @staticmethod
    def _display_cwd(raw_cwd: str) -> str:
        if not raw_cwd.strip():
            return "."
        path = Path(raw_cwd).expanduser()
        if not path.is_absolute():
            return raw_cwd
        resolved = path.resolve()
        try:
            return resolved.relative_to(PROJECT_ROOT).as_posix() or "."
        except ValueError:
            return str(resolved)

    @staticmethod
    def _first_run_script_command(script: str) -> str:
        for line in script.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") or stripped.startswith("#!"):
                continue
            if stripped.startswith("set ") or stripped.startswith("conda "):
                continue
            if "<" in stripped or "TODO" in stripped:
                continue
            if not stripped.startswith(("python ", "pip ", "bash ", "sh ")):
                continue
            return stripped
        return ""

    def _locate_action_locked(
        self,
        action_id: str,
    ) -> tuple[str, int, ActionRequest] | None:
        for run_id, actions in self._actions.items():
            for index, action in enumerate(actions):
                if action.action_id == action_id:
                    return run_id, index, action
        return None

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
