"""Static Python and dependency analysis tools."""

from __future__ import annotations

import ast
from pathlib import Path

from tools.file_tools import resolve_allowed_path


def python_ast_summary(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> dict[str, object]:
    resolved = resolve_allowed_path(path, allowed_roots)
    tree = ast.parse(resolved.read_text(encoding="utf-8"))
    functions = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return {
        "path": str(resolved),
        "functions": sorted(functions),
        "classes": sorted(classes),
        "imports": sorted(set(imports)),
    }


def extract_functions_classes(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> dict[str, list[str]]:
    summary = python_ast_summary(path, allowed_roots=allowed_roots)
    return {
        "functions": list(summary["functions"]),
        "classes": list(summary["classes"]),
    }


def extract_cli_args(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> list[str]:
    resolved = resolve_allowed_path(path, allowed_roots)
    tree = ast.parse(resolved.read_text(encoding="utf-8"))
    arguments: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    arguments.append(arg.value)
    return arguments


def parse_dependency_file(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> dict[str, object]:
    from tools.env_tools import parse_environment_yml, parse_pyproject, parse_requirements

    resolved = resolve_allowed_path(path, allowed_roots)
    if resolved.name == "requirements.txt":
        return {"format": "requirements", **parse_requirements(resolved, allowed_roots=allowed_roots)}
    if resolved.name == "pyproject.toml":
        return {"format": "pyproject", **parse_pyproject(resolved, allowed_roots=allowed_roots)}
    if resolved.suffix.lower() in {".yaml", ".yml"}:
        return {"format": "conda", **parse_environment_yml(resolved, allowed_roots=allowed_roots)}
    raise ValueError(f"Unsupported dependency file: {resolved.name}")
