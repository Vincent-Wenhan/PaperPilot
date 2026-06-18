"""Deterministic implementation blueprint helpers for reproduction projects."""

from __future__ import annotations

import ast
import re

from schemas.reproduction_schema import (
    BlueprintFile,
    ImplementationBlueprint,
    ImplementationBundle,
    MethodModule,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
)

SMOKE_TEST_COMMAND = "python main.py --smoke-test"
STATIC_BLUEPRINT_PATHS = {
    "README.md",
    "config.py",
    "main.py",
    "tests/test_dataflow.py",
    "requirements.txt",
}


def _safe_project_name(title: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return cleaned or "paperpilot_reproduction"


def _safe_module_stem(name: str, index: int) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return cleaned or f"module_{index}"


def _required_symbol(name: str, index: int) -> str:
    return f"run_{_safe_module_stem(name, index)}"


def _unique_module_path(stem: str, index: int, used_paths: set[str]) -> str:
    candidate = f"{stem}.py"
    if candidate not in used_paths:
        used_paths.add(candidate)
        return candidate

    candidate = f"{stem}_{index}.py"
    suffix = index
    while candidate in used_paths:
        suffix += 1
        candidate = f"{stem}_{suffix}.py"
    used_paths.add(candidate)
    return candidate


def _module_blueprint_file(
    module: MethodModule, index: int, used_paths: set[str]
) -> BlueprintFile:
    stem = _safe_module_stem(module.name, index)
    symbol = _required_symbol(module.name, index)
    responsibility = module.purpose or f"Implement method module {stem}"
    return BlueprintFile(
        path=_unique_module_path(stem, index, used_paths),
        responsibility=responsibility,
        required_symbols=[symbol],
        test_relevance=f"Dataflow test imports {symbol} and verifies smoke behavior.",
    )


def _assignment_target_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_assignment_target_names(element))
        return names
    return set()


def _python_declared_symbols(content: str) -> set[str]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    symbols: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                symbols.update(_assignment_target_names(target))
        elif isinstance(node, ast.AnnAssign):
            symbols.update(_assignment_target_names(node.target))
        elif isinstance(node, ast.AugAssign):
            symbols.update(_assignment_target_names(node.target))
    return symbols


def _content_declares_symbol(path: str, content: str, symbol: str) -> bool:
    if path.endswith(".py"):
        return symbol in _python_declared_symbols(content)
    return symbol in content


def build_implementation_blueprint(
    paper: PaperUnderstanding,
    repository: RepositoryUnderstanding,
    plan: ReproductionPlan,
    *,
    hardware: str = "",
    goal: str = "",
) -> ImplementationBlueprint:
    """Build a conservative, deterministic file-level implementation blueprint."""

    objective = goal or plan.goal or "minimal training experiment"
    project_name = _safe_project_name(paper.title)
    framework = repository.detected_framework or "unknown"
    strategy = plan.implementation_strategy or "Create a minimal runnable reproduction."
    dataflow = list(paper.end_to_end_dataflow)
    if not dataflow:
        dataflow = [
            "Create deterministic synthetic inputs",
            "Run the implemented method path",
            "Report smoke-test metrics",
        ]

    files = [
        BlueprintFile(
            path="README.md",
            responsibility="Document the reproduction scope, setup, and smoke command.",
            test_relevance="Explains how to run the generated project.",
        ),
        BlueprintFile(
            path="requirements.txt",
            responsibility=f"List minimal dependencies for {framework} reproduction.",
            test_relevance="Supports environment creation for the smoke run.",
        ),
        BlueprintFile(
            path="config.py",
            responsibility="Centralize deterministic defaults, seeds, and hardware settings.",
            required_symbols=["DEFAULT_SEED", "HARDWARE_TARGET"],
            test_relevance="Dataflow test can assert stable configuration values.",
        ),
    ]

    used_paths = set(STATIC_BLUEPRINT_PATHS)
    module_files = [
        _module_blueprint_file(module, index, used_paths)
        for index, module in enumerate(paper.method_modules[:3], start=1)
    ]
    if not module_files:
        module_files = [
            BlueprintFile(
                path="model.py",
                responsibility="Implement a conservative fallback model path.",
                required_symbols=["run_model"],
                test_relevance="Smoke test exercises the fallback model.",
            )
        ]

    files.extend(module_files)
    files.extend(
        [
            BlueprintFile(
                path="main.py",
                responsibility="Provide CLI orchestration for the full smoke dataflow.",
                required_symbols=["main"],
                test_relevance="Runs with python main.py --smoke-test.",
            ),
            BlueprintFile(
                path="tests/test_dataflow.py",
                responsibility="Validate that the smoke dataflow executes end to end.",
                required_symbols=["test_smoke_dataflow"],
                test_relevance="Guards the generated reproduction against broken wiring.",
            ),
        ]
    )

    return ImplementationBlueprint(
        project_name=project_name,
        objective=objective,
        architecture_summary=(
            f"{strategy} Target hardware: {hardware or 'unspecified'}. "
            f"Detected framework: {framework}."
        ),
        files=files,
        core_dataflow=dataflow,
        required_entrypoints=[SMOKE_TEST_COMMAND],
        quality_requirements=[
            "Use deterministic synthetic data when real data is unavailable.",
            "Keep the smoke test CPU-compatible and fast.",
            "Document assumptions and fidelity limits in README.md.",
        ],
        forbidden_patterns=[
            "Do not require unavailable private datasets or checkpoints.",
            "Do not silently download large artifacts during smoke tests.",
            "Do not leave placeholder pass-only implementations for core modules.",
        ],
    )


def assess_blueprint_coverage(
    bundle: ImplementationBundle, blueprint: ImplementationBlueprint
) -> dict[str, object]:
    """Assess whether generated files cover required blueprint paths and symbols."""

    generated_by_path = {item.path: item for item in bundle.files}
    missing_files = [
        item.path for item in blueprint.files if item.path not in generated_by_path
    ]
    missing_symbols: list[str] = []
    for item in blueprint.files:
        generated = generated_by_path.get(item.path)
        if generated is None:
            continue
        for symbol in item.required_symbols:
            if symbol and not _content_declares_symbol(
                item.path, generated.content, symbol
            ):
                missing_symbols.append(f"{item.path}:{symbol}")

    missing_entrypoints = [
        command
        for command in blueprint.required_entrypoints
        if command != bundle.smoke_test_command
    ]

    issue_codes: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []
    if missing_files:
        issue_codes.append("missing_blueprint_files")
        issues.append("Missing planned files: " + ", ".join(missing_files))
        suggestions.append("Generate every file listed in the implementation blueprint.")
    if missing_symbols:
        issue_codes.append("missing_required_symbols")
        issues.append("Missing required symbols: " + ", ".join(missing_symbols))
        suggestions.append("Add the required public functions/constants to generated files.")
    if missing_entrypoints:
        issue_codes.append("missing_required_entrypoints")
        issues.append("Missing required entrypoints: " + ", ".join(missing_entrypoints))
        suggestions.append("Set the bundle smoke test command to the blueprint entrypoint.")

    planned_count = len(blueprint.files)
    present_count = planned_count - len(missing_files)
    metrics = {
        "planned_file_count": planned_count,
        "generated_file_count": len(bundle.files),
        "covered_file_count": present_count,
        "missing_file_count": len(missing_files),
        "missing_symbol_count": len(missing_symbols),
        "missing_entrypoint_count": len(missing_entrypoints),
    }

    return {
        "passes_blueprint_coverage": not issue_codes,
        "issue_codes": issue_codes,
        "issues": issues,
        "suggestions": suggestions,
        "metrics": metrics,
    }
