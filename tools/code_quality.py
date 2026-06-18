"""Deterministic quality checks for generated reproduction code."""

from __future__ import annotations

import ast
import re
from typing import Any

from schemas.reproduction_schema import ImplementationBlueprint, ImplementationBundle
from tools.implementation_blueprint import assess_blueprint_coverage


PLACEHOLDER_PATTERNS = (
    re.compile(r"\bpass\b"),
    re.compile(r"raise\s+NotImplementedError"),
    re.compile(r"\.\.\."),
)
GENERIC_TEXT_PATTERNS = (
    "generic placeholder",
    "mock reproduction",
    "real paper method remains unimplemented",
    "add paper-specific dependencies",
)


def _normalized_paths(bundle: ImplementationBundle) -> list[str]:
    return [
        item.path.strip().replace("\\", "/").lower()
        for item in bundle.files
        if item.path.strip()
    ]


def _python_complexity(source: str) -> dict[str, int]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"functions": 0, "classes": 0}
    functions = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(tree)
    )
    classes = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    return {"functions": functions, "classes": classes}


def assess_implementation_quality(
    bundle: ImplementationBundle,
    blueprint: ImplementationBlueprint | None = None,
) -> dict[str, Any]:
    """Score a generated implementation bundle without executing its code."""
    paths = _normalized_paths(bundle)
    python_files = [
        item for item in bundle.files if item.path.strip().lower().endswith(".py")
    ]
    tests = [
        path
        for path in paths
        if path.startswith("tests/") and path.endswith(".py")
    ]
    has_readme = "readme.md" in paths
    has_config = any(path in {"config.py", "settings.py"} for path in paths)
    has_entrypoint = any(path in {"main.py", "app.py", "run.py"} for path in paths)
    has_requirements = "requirements.txt" in paths

    issue_codes: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []
    blueprint_quality = (
        assess_blueprint_coverage(bundle, blueprint)
        if blueprint is not None
        else {
            "passes_blueprint_coverage": True,
            "issue_codes": [],
            "issues": [],
            "suggestions": [],
            "metrics": {},
        }
    )

    all_text = "\n".join(item.content for item in bundle.files).lower()
    if not python_files:
        issue_codes.append("missing_python")
        issues.append("Generated bundle does not include a Python implementation file.")
        suggestions.append("Add at least one Python module that implements the method dataflow.")
    if not tests:
        issue_codes.append("missing_tests")
        issues.append("Generated bundle does not include tests under tests/.")
        suggestions.append("Add a smoke or dataflow test under tests/.")
    if not has_readme:
        issue_codes.append("missing_readme")
        issues.append("Generated bundle does not include README.md.")
        suggestions.append("Document implemented scope, assumptions, and validation steps.")
    if not has_entrypoint:
        issue_codes.append("missing_entrypoint")
        issues.append("Generated bundle does not include a runnable entry point.")
        suggestions.append("Add main.py with a safe --smoke-test path.")
    if any(
        pattern.search(item.content)
        for item in python_files
        for pattern in PLACEHOLDER_PATTERNS
    ):
        issue_codes.append("placeholder_body")
        issues.append("Generated Python source contains placeholder bodies.")
        suggestions.append("Replace placeholder bodies with minimal runnable logic.")
    if any(pattern in all_text for pattern in GENERIC_TEXT_PATTERNS):
        issue_codes.append("generic_template_language")
        issues.append("Generated content still contains generic scaffold language.")
        suggestions.append("Use paper-specific module names, dataflow, and validation descriptions.")

    complexity = {"functions": 0, "classes": 0}
    for item in python_files:
        item_complexity = _python_complexity(item.content)
        complexity["functions"] += item_complexity["functions"]
        complexity["classes"] += item_complexity["classes"]
    if len(python_files) == 1 and complexity["functions"] <= 1 and complexity["classes"] == 0:
        issue_codes.append("thin_single_file")
        issues.append("Generated implementation is a thin single-file scaffold.")
        suggestions.append("Separate configuration, method modules, and entry point when justified.")

    for code in blueprint_quality["issue_codes"]:
        if code not in issue_codes:
            issue_codes.append(str(code))
    for issue in blueprint_quality["issues"]:
        issue_text = str(issue)
        if issue_text not in issues:
            issues.append(issue_text)
    for suggestion in blueprint_quality["suggestions"]:
        suggestion_text = str(suggestion)
        if suggestion_text not in suggestions:
            suggestions.append(suggestion_text)

    score = 5.0
    score -= 1.0 if "placeholder_body" in issue_codes else 0.0
    score -= 0.8 if "missing_tests" in issue_codes else 0.0
    score -= 0.7 if "generic_template_language" in issue_codes else 0.0
    score -= 0.6 if "missing_readme" in issue_codes else 0.0
    score -= 0.6 if "missing_entrypoint" in issue_codes else 0.0
    score -= 0.6 if "missing_python" in issue_codes else 0.0
    score -= 0.5 if "thin_single_file" in issue_codes else 0.0
    if has_config:
        score += 0.2
    if has_requirements:
        score += 0.1
    if len(python_files) >= 3 and complexity["functions"] + complexity["classes"] >= 4:
        score += 0.3
    overall_score = max(1.0, min(5.0, round(score, 2)))

    blueprint_metrics = dict(blueprint_quality["metrics"])
    if "planned_file_count" in blueprint_metrics:
        blueprint_metrics.setdefault(
            "planned_files",
            blueprint_metrics["planned_file_count"],
        )
    if "missing_file_count" in blueprint_metrics:
        blueprint_metrics.setdefault(
            "missing_files",
            blueprint_metrics["missing_file_count"],
        )

    return {
        "overall_score": overall_score,
        "passes_minimum_quality": (
            overall_score >= 3.5
            and not {
                "placeholder_body",
                "missing_python",
                "missing_tests",
            }.intersection(issue_codes)
            and bool(blueprint_quality["passes_blueprint_coverage"])
        ),
        "issue_codes": issue_codes,
        "issues": issues,
        "suggestions": suggestions,
        "metrics": {
            "files": len(paths),
            "python_files": len(python_files),
            "has_tests": bool(tests),
            "has_readme": has_readme,
            "has_config": has_config,
            "has_entrypoint": has_entrypoint,
            "has_requirements": has_requirements,
            "functions": complexity["functions"],
            "classes": complexity["classes"],
            "blueprint": blueprint_metrics,
        },
    }
