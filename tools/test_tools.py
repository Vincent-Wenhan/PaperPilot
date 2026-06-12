"""Safe validation tools that do not execute application bodies."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from productize.product_tester import inspect_generated_product
from tools.file_tools import resolve_allowed_path


def python_syntax_check(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> dict[str, object]:
    resolved = resolve_allowed_path(path, allowed_roots)
    try:
        source = resolved.read_text(encoding="utf-8")
        compile(source, str(resolved), "exec")
    except (OSError, SyntaxError, UnicodeError) as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "error": ""}


def compileall_check(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> dict[str, object]:
    resolved = resolve_allowed_path(path, allowed_roots)
    failures: list[dict[str, str]] = []
    for source_path in sorted(resolved.rglob("*.py")):
        try:
            source = source_path.read_text(encoding="utf-8")
            compile(source, str(source_path), "exec")
        except (OSError, SyntaxError, UnicodeError) as exc:
            failures.append(
                {
                    "path": source_path.relative_to(resolved).as_posix(),
                    "error": str(exc),
                }
            )
    return {
        "success": not failures,
        "path": str(resolved),
        "failures": failures,
    }


def pytest_collect(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
    timeout: int = 60,
) -> dict[str, object]:
    resolved = resolve_allowed_path(path, allowed_roots)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            str(resolved),
        ],
        cwd=str(resolved),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def generated_product_inspect(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> dict[str, object]:
    resolved = resolve_allowed_path(path, allowed_roots)
    return inspect_generated_product(resolved)
