"""Static environment and dependency parsers."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import yaml

from tools.file_tools import resolve_allowed_path


def parse_requirements(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> dict[str, Any]:
    resolved = resolve_allowed_path(path, allowed_roots)
    packages: list[dict[str, str]] = []
    for raw in resolved.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)(.*)", line)
        if match:
            packages.append({"name": match.group(1), "specifier": match.group(2)})
    return {"path": str(resolved), "packages": packages}


def parse_pyproject(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> dict[str, Any]:
    resolved = resolve_allowed_path(path, allowed_roots)
    data = tomllib.loads(resolved.read_text(encoding="utf-8"))
    project = data.get("project") or {}
    return {
        "path": str(resolved),
        "requires_python": project.get("requires-python", ""),
        "dependencies": project.get("dependencies", []),
    }


def parse_environment_yml(
    path: str | Path,
    *,
    allowed_roots: list[str | Path],
) -> dict[str, Any]:
    resolved = resolve_allowed_path(path, allowed_roots)
    data = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    return {
        "path": str(resolved),
        "name": data.get("name", ""),
        "dependencies": data.get("dependencies", []),
        "channels": data.get("channels", []),
    }


def detect_cuda_requirement(environment: dict[str, Any]) -> bool:
    text = str(environment).lower()
    return any(token in text for token in ("cuda", "cudnn", "pytorch", "torch"))


def detect_python_version(environment: dict[str, Any]) -> str:
    text = str(environment)
    match = re.search(r"python(?:=|>=|==|: '?)(\d+(?:\.\d+)*)", text, re.IGNORECASE)
    return match.group(1) if match else ""
