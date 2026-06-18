"""Reviewed command service backed by the existing PaperPilot Runner policy."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from backend.schemas import (
    CommandReviewRequest,
    CommandReviewResult,
    CommandRunRequest,
    CommandRunResult,
)
from config import PROJECT_ROOT
from tools.command_runner import plan_command, run_command_review
from tools.file_tools import resolve_allowed_path


class CommandService:
    def __init__(self, *, project_root: Path = PROJECT_ROOT) -> None:
        self.project_root = Path(project_root).resolve()
        self.command_roots = [self.project_root, self.project_root / "workspace"]
        self._results: dict[str, list[CommandRunResult]] = {}

    def review_command(
        self,
        run_id: str,
        request: CommandReviewRequest,
    ) -> CommandReviewResult:
        cwd = resolve_allowed_path(
            self.project_root / request.cwd,
            self.command_roots,
        )
        plan = plan_command(request.command)
        return CommandReviewResult(
            run_id=run_id,
            command=request.command,
            cwd=cwd.relative_to(self.project_root).as_posix() or ".",
            risk_level=plan.risk_level,
            requires_confirmation=plan.requires_confirmation,
            blocked_reason=plan.blocked_reason,
        )

    def run_command(
        self,
        run_id: str,
        request: CommandRunRequest,
    ) -> CommandRunResult:
        cwd = resolve_allowed_path(
            self.project_root / request.cwd,
            self.command_roots,
        )
        result = run_command_review(
            request.command,
            cwd,
            timeout=request.timeout,
            mode=request.mode,
        )
        api_result = CommandRunResult(
            run_id=run_id,
            command=result.command,
            cwd=cwd.relative_to(self.project_root).as_posix() or ".",
            mode=result.mode,
            executed=result.executed,
            risk_level=result.risk_level,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            blocked_reason=result.blocked_reason,
        )
        self._results.setdefault(run_id, []).append(api_result)
        return deepcopy(api_result)

    def list_results(self, run_id: str) -> list[CommandRunResult]:
        return deepcopy(self._results.get(run_id, []))


command_service = CommandService()
