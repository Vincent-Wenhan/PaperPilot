"""Read-only repository structure scanner."""

from __future__ import annotations

from pathlib import Path
from typing import Any


IMPORTANT_NAMES = {
    "README.md",
    "README.rst",
    "README.txt",
    "requirements.txt",
    "environment.yml",
    "environment.yaml",
    "setup.py",
    "pyproject.toml",
    "train.py",
    "main.py",
    "eval.py",
    "test.py",
    "demo.py",
}
IMPORTANT_DIRECTORIES = {"scripts", "configs", "examples", "notebooks"}
ENTRYPOINT_NAMES = {"train.py", "main.py", "eval.py", "test.py", "demo.py", "run.py", "inference.py", "app.py", "server.py"}
CONFIG_SUFFIXES = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"}
SKIPPED_DIRECTORIES = {".git", "__pycache__", ".venv", "venv", "node_modules"}

FRAMEWORK_PATTERNS: dict[str, list[str]] = {
    "pytorch": ["import torch", "from torch", "import torchvision", "from torchvision"],
    "tensorflow": ["import tensorflow", "from tensorflow", "import tf", "from tf"],
    "jax": ["import jax", "from jax", "import flax", "from flax"],
    "sklearn": ["import sklearn", "from sklearn"],
    "lightning": ["import lightning", "from lightning", "import pytorch_lightning", "from pytorch_lightning"],
    "keras": ["import keras", "from keras", "import tf.keras"],
}

CONFIG_PATTERNS: dict[str, list[str]] = {
    "hydra": ["from hydra", "import hydra", "@hydra"],
    "argparse": ["import argparse", "from argparse", "argparse.ArgumentParser"],
    "yaml": ["import yaml", "from yaml", "import omegaconf", "from omegaconf"],
    "json": ["import json", "from json"],
    "toml": ["import toml", "from toml", "import tomllib", "from tomllib"],
    "click": ["import click", "from click", "@click.command"],
}

RISK_DATASET_KEYWORDS = [
    "imagenet", "coco", "cityscapes", "lsun", "places365",
    "kinetics", "audioset", "librispeech", "squad", "glue",
]


def _read_text(path: Path, max_chars: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError as exc:
        return f"[Unable to read {path.name}: {exc}]"


def _relative_paths(paths: list[Path], root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in paths)


def scan_repo(
    repo_path: str | Path,
    max_file_chars: int = 12_000,
) -> dict[str, Any]:
    """Scan a local repository without executing any of its contents."""
    root = Path(repo_path).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Repository directory does not exist: {root}")
    if max_file_chars <= 0:
        raise ValueError("max_file_chars must be a positive integer.")

    files: list[Path] = []
    directories: list[Path] = []
    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        if any(part in SKIPPED_DIRECTORIES for part in relative_parts):
            continue
        if path.is_symlink():
            continue
        if path.is_dir():
            directories.append(path)
        elif path.is_file():
            files.append(path)

    important_files = [
        path for path in files if path.name in IMPORTANT_NAMES
    ]
    important_directories = [
        path for path in directories if path.name in IMPORTANT_DIRECTORIES
    ]
    entrypoints = [
        path
        for path in files
        if path.name in ENTRYPOINT_NAMES
        or (
            len(path.relative_to(root).parts) >= 2
            and path.relative_to(root).parts[0] == "examples"
            and path.name.endswith(".py")
        )
    ]
    config_files = [
        path
        for path in files
        if path.suffix.lower() in CONFIG_SUFFIXES
        or "config" in path.name.lower()
    ]

    readme = next(
        (path for path in files if path.name.lower().startswith("readme")),
        None,
    )
    requirements = next(
        (path for path in files if path.name == "requirements.txt"),
        None,
    )
    environment = next(
        (
            path
            for path in files
            if path.name in {"environment.yml", "environment.yaml"}
        ),
        None,
    )
    setup_file = next(
        (path for path in files if path.name in {"setup.py", "pyproject.toml"}),
        None,
    )

    return {
        "repo_path": str(root),
        "important_files": _relative_paths(important_files, root),
        "directories": _relative_paths(directories, root),
        "important_directories": _relative_paths(important_directories, root),
        "possible_entrypoints": _relative_paths(entrypoints, root),
        "config_files": _relative_paths(config_files, root),
        "readme_content": _read_text(readme, max_file_chars) if readme else "",
        "requirements_content": (
            _read_text(requirements, max_file_chars) if requirements else ""
        ),
        "environment_content": (
            _read_text(environment, max_file_chars) if environment else ""
        ),
        "setup_content": (
            _read_text(setup_file, max_file_chars) if setup_file else ""
        ),
    }


def _detect_framework(file_texts: list[str]) -> str:
    """Scan file contents to detect the primary ML framework."""
    combined = "\n".join(file_texts).lower()
    for framework, patterns in FRAMEWORK_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in combined:
                return framework
    return "unknown"


def _detect_config_systems(file_texts: list[str]) -> list[str]:
    """Detect configuration libraries used in the repo."""
    combined = "\n".join(file_texts)
    detected: list[str] = []
    for system, patterns in CONFIG_PATTERNS.items():
        for pattern in patterns:
            if pattern in combined:
                detected.append(system)
                break
    return detected


def _detect_risk_signals(
    repo_path: Path,
    has_any_requirements: bool,
    has_readme: bool,
    readme_content: str,
) -> list[dict[str, str]]:
    """Identify potential reproduction risks."""
    risks: list[dict[str, str]] = []

    if not has_any_requirements:
        risks.append({"signal": "missing_requirements", "detail": "No requirements.txt, environment.yml, setup.py, or pyproject.toml found"})
    if not has_readme:
        risks.append({"signal": "no_readme", "detail": "No README file found"})

    if has_readme and readme_content:
        readme_lower = readme_content.lower()
        ckpt_keywords = ["checkpoint", "pretrained", "pretrain", "weights", "model zoo", "modelzoo", "download"]
        if not any(kw in readme_lower for kw in ckpt_keywords):
            risks.append({"signal": "no_checkpoint_link", "detail": "README does not mention checkpoints, pretrained weights, or model zoo"})

        if any(ds in readme_lower for ds in RISK_DATASET_KEYWORDS):
            risks.append({"signal": "large_dataset_required", "detail": "README mentions a large-scale dataset that may be difficult to obtain"})

    py_files = list(repo_path.rglob("*.py"))
    for py_file in py_files:
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(p in content for p in ["/data/", "/home/", "/mnt/", "C:\\Users", "/scratch/"]):
            risks.append({"signal": "hardcoded_paths", "detail": f"Hardcoded absolute paths detected in {py_file.relative_to(repo_path)}"})
            break

    cu_files = list(repo_path.rglob("*.cu")) + list(repo_path.rglob("*.cuh"))
    if cu_files:
        risks.append({"signal": "cuda_extension", "detail": f"CUDA source files detected ({len(cu_files)} files); may require custom compilation"})

    return risks


def _has_training_code(entrypoints: list[str]) -> bool:
    return any("train" in ep for ep in entrypoints)


def _has_inference_code(entrypoints: list[str]) -> bool:
    combined = " ".join(entrypoints)
    return any(kw in combined for kw in ["infer", "eval", "test", "demo", "app", "predict"])


def scan_repo_detailed(
    repo_path: str | Path,
    max_file_chars: int = 12_000,
) -> dict[str, Any]:
    """Scan repo with structured evidence: framework, config, risks."""
    scan_result = scan_repo(repo_path, max_file_chars)
    root = Path(repo_path).expanduser().resolve()

    py_texts: list[str] = []
    py_files = list(root.rglob("*.py"))
    for py_file in py_files:
        try:
            parts = py_file.relative_to(root).parts
            if any(part in SKIPPED_DIRECTORIES for part in parts):
                continue
            py_texts.append(py_file.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue

    framework = _detect_framework(py_texts)
    entrypoints = [ep for ep in scan_result.get("possible_entrypoints", [])]
    has_readme = bool(scan_result.get("readme_content", ""))
    has_reqs = bool(scan_result.get("requirements_content", ""))
    has_env = bool(scan_result.get("environment_content", ""))
    has_setup = bool(scan_result.get("setup_content", ""))
    has_any_requirements = has_reqs or has_env or has_setup

    risks = _detect_risk_signals(root, has_any_requirements, has_readme, scan_result.get("readme_content", ""))
    config_systems = _detect_config_systems(py_texts)

    notes: list[str] = []
    if framework != "unknown":
        notes.append(f"Detected {framework} framework")
    for cs in config_systems:
        notes.append(f"Detected {cs} configuration system")
    if entrypoints:
        notes.append(f"Found {len(entrypoints)} entrypoint(s): {', '.join(entrypoints[:5])}")
    if not risks:
        notes.append("No significant reproduction risks detected")

    repo_name = root.name

    return {
        **scan_result,
        "repo_name": repo_name,
        "detected_framework": framework,
        "main_language": "python",
        "has_training_code": _has_training_code(entrypoints),
        "has_inference_code": _has_inference_code(entrypoints),
        "config_systems": config_systems,
        "risk_signals": [r["signal"] for r in risks],
        "reproduction_risks": [r["detail"] for r in risks],
        "notes": notes,
    }
