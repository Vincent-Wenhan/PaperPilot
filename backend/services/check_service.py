"""Static code checks for generated workbench files."""

from __future__ import annotations

from pathlib import Path

from backend.schemas import SyntaxCheckRequest, SyntaxCheckResult
from config import OUTPUTS_DIR, PROJECT_ROOT, WORKSPACE_DIR
from tools.file_tools import resolve_allowed_path
from tools.test_tools import compileall_check, python_syntax_check


class CheckService:
    def __init__(
        self,
        *,
        project_root: Path = PROJECT_ROOT,
        check_roots: list[Path] | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.check_roots = [
            Path(root).resolve()
            for root in (
                check_roots
                or [
                    WORKSPACE_DIR,
                    OUTPUTS_DIR,
                    PROJECT_ROOT / "generated_product",
                    PROJECT_ROOT / "examples" / "sample_outputs",
                ]
            )
        ]

    def syntax_check(self, request: SyntaxCheckRequest) -> SyntaxCheckResult:
        resolved = resolve_allowed_path(
            self.project_root / request.path,
            self.check_roots,
        )
        if request.recursive or resolved.is_dir():
            result = compileall_check(resolved, allowed_roots=self.check_roots)
            return SyntaxCheckResult(
                path=resolved.relative_to(self.project_root).as_posix(),
                success=bool(result["success"]),
                failures=list(result["failures"]),
            )
        result = python_syntax_check(resolved, allowed_roots=self.check_roots)
        return SyntaxCheckResult(
            path=resolved.relative_to(self.project_root).as_posix(),
            success=bool(result["success"]),
            failures=[],
            error=str(result["error"]),
        )


check_service = CheckService()
