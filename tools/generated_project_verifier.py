"""Contract-based verifier for generated reproduction projects."""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VerificationIssue:
    code: str
    message: str
    file: str = ""
    severity: str = "medium"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class VerificationReport:
    ok: bool
    syntax_ok: bool
    tests_collect_ok: bool
    smoke_ok: bool
    schema_ok: bool
    issues: list[VerificationIssue] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class GeneratedProjectVerifier:
    """Verify a generated project against an executable implementation contract."""

    def __init__(
        self,
        project_dir: str | Path,
        contract: dict[str, Any],
        timeout: int = 20,
    ) -> None:
        self.project_dir = Path(project_dir).expanduser().resolve()
        self.contract = contract
        self.timeout = timeout

    def verify(self) -> VerificationReport:
        issues: list[VerificationIssue] = []

        project_dir_ok = self._check_project_dir(issues)
        if not project_dir_ok:
            return VerificationReport(
                ok=False,
                syntax_ok=False,
                tests_collect_ok=False,
                smoke_ok=False,
                schema_ok=False,
                issues=issues,
            )

        files_ok = self._check_required_files(issues)
        syntax_ok = self._check_python_syntax(issues)
        tests_collect_ok = self._pytest_collect(issues)
        smoke_ok, stdout, stderr = self._run_smoke(issues)
        schema_ok = self._check_output_schema(issues)
        claims_ok = self._check_forbidden_claims(issues)

        return VerificationReport(
            ok=files_ok
            and syntax_ok
            and tests_collect_ok
            and smoke_ok
            and schema_ok
            and claims_ok,
            syntax_ok=syntax_ok,
            tests_collect_ok=tests_collect_ok,
            smoke_ok=smoke_ok,
            schema_ok=schema_ok,
            issues=issues,
            stdout=stdout,
            stderr=stderr,
        )

    def _check_project_dir(self, issues: list[VerificationIssue]) -> bool:
        if self.project_dir.is_dir():
            return True
        issues.append(
            VerificationIssue(
                code="missing_project_dir",
                file=str(self.project_dir),
                message=f"Generated project directory does not exist: {self.project_dir}",
                severity="high",
            )
        )
        return False

    def _check_required_files(self, issues: list[VerificationIssue]) -> bool:
        ok = True
        required = [
            *self.contract.get("required_files", []),
            *self.contract.get("required_tests", []),
        ]
        for rel in sorted({str(item) for item in required if str(item)}):
            if not (self.project_dir / rel).is_file():
                ok = False
                issues.append(
                    VerificationIssue(
                        code="missing_required_file",
                        file=rel,
                        message=f"Required file is missing: {rel}",
                        severity="high",
                    )
                )
        return ok

    def _check_python_syntax(self, issues: list[VerificationIssue]) -> bool:
        ok = True
        for path in self.project_dir.rglob("*.py"):
            if any(part in {".git", "__pycache__", ".venv", "venv"} for part in path.parts):
                continue
            source = path.read_text(encoding="utf-8")
            try:
                compile(source, str(path), "exec")
            except SyntaxError as exc:
                ok = False
                issues.append(
                    VerificationIssue(
                        code="syntax_error",
                        file=str(path.relative_to(self.project_dir)),
                        message=f"{exc.msg} at line {exc.lineno}",
                        severity="high",
                    )
                )
        return ok

    def _pytest_collect(self, issues: list[VerificationIssue]) -> bool:
        tests_dir = self.project_dir / "tests"
        if not tests_dir.exists():
            issues.append(
                VerificationIssue(
                    code="missing_tests",
                    message="No tests/ directory found.",
                    severity="medium",
                )
            )
            return False

        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            issues.append(
                VerificationIssue(
                    code="pytest_collect_failed",
                    message=(result.stderr or result.stdout)[-2000:],
                    severity="high",
                )
            )
            return False
        return True

    def _run_smoke(self, issues: list[VerificationIssue]) -> tuple[bool, str, str]:
        command = self.contract.get("smoke_test_command") or ["python", "main.py", "--smoke-test"]
        args = [str(item) for item in command] if isinstance(command, list) else shlex.split(str(command))
        result = subprocess.run(
            args,
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            issues.append(
                VerificationIssue(
                    code="smoke_failed",
                    message=(result.stderr or result.stdout)[-2000:],
                    severity="high",
                )
            )
            return False, result.stdout, result.stderr
        return True, result.stdout, result.stderr

    def _check_output_schema(self, issues: list[VerificationIssue]) -> bool:
        expected = self.contract.get("output_schema") or {}
        if not expected:
            return True

        output_path = self.project_dir / "outputs" / "result.json"
        if not output_path.exists():
            issues.append(
                VerificationIssue(
                    code="missing_output_json",
                    file="outputs/result.json",
                    message="Smoke test did not produce outputs/result.json.",
                    severity="high",
                )
            )
            return False

        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(
                VerificationIssue(
                    code="invalid_output_json",
                    file="outputs/result.json",
                    message=str(exc),
                    severity="high",
                )
            )
            return False

        missing = [key for key in expected if key not in data]
        mismatched = [
            key
            for key, expected_type in expected.items()
            if key in data and not self._matches_type(data[key], str(expected_type))
        ]
        if missing or mismatched:
            details = []
            if missing:
                details.append(f"missing fields: {missing}")
            if mismatched:
                details.append(f"type mismatches: {mismatched}")
            issues.append(
                VerificationIssue(
                    code="output_schema_mismatch",
                    file="outputs/result.json",
                    message="; ".join(details),
                    severity="high",
                )
            )
            return False
        return True

    def _check_forbidden_claims(self, issues: list[VerificationIssue]) -> bool:
        patterns = [str(item).lower() for item in self.contract.get("forbidden_patterns", []) if str(item)]
        if not patterns:
            return True
        ok = True
        for path in self.project_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".py", ".json"}:
                continue
            if any(part in {".git", "__pycache__", ".venv", "venv"} for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            matched = [pattern for pattern in patterns if pattern in text]
            if matched:
                ok = False
                issues.append(
                    VerificationIssue(
                        code="forbidden_claim",
                        file=str(path.relative_to(self.project_dir)),
                        message=f"Forbidden claim(s) found: {matched}",
                        severity="medium",
                    )
                )
        return ok

    @staticmethod
    def _matches_type(value: Any, expected_type: str) -> bool:
        normalized = expected_type.lower()
        if normalized in {"number", "float", "int", "integer"}:
            return isinstance(value, int | float) and not isinstance(value, bool)
        if normalized in {"array", "list"}:
            return isinstance(value, list)
        if normalized in {"object", "dict"}:
            return isinstance(value, dict)
        if normalized in {"string", "str"}:
            return isinstance(value, str)
        if normalized in {"boolean", "bool"}:
            return isinstance(value, bool)
        return True
