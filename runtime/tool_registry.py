"""Explicit registry for deterministic PaperPilot tools."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from schemas.tool_schema import ToolSpec


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    function: Callable[..., Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, function: Callable[..., Any]) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = RegisteredTool(spec=spec, function=function)

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def list_specs(self) -> list[ToolSpec]:
        return [item.spec for item in self._tools.values()]


def build_default_registry() -> ToolRegistry:
    """Build the explicit registry of deterministic tools shipped by PaperPilot."""
    from tools.code_analysis_tools import (
        extract_cli_args,
        extract_functions_classes,
        parse_dependency_file,
        python_ast_summary,
    )
    from tools.code_search_tools import (
        code_search,
        find_checkpoint_keywords,
        find_dataset_paths,
        find_entrypoints,
        find_todo_or_missing,
    )
    from tools.env_tools import (
        detect_cuda_requirement,
        detect_python_version,
        parse_environment_yml,
        parse_pyproject,
        parse_requirements,
    )
    from tools.file_tools import list_dir, read_file, read_many_files, tree_view
    from tools.test_tools import (
        compileall_check,
        generated_product_inspect,
        pytest_collect,
        python_syntax_check,
    )

    registry = ToolRegistry()
    read_agents = [
        "Research Understanding Agent",
        "Repository Understanding Agent",
        "Reproduction Planner Agent",
        "Reproduction Implementation Agent",
        "Research Synthesizer Agent",
        "Product Planner Agent",
        "Product Evaluator Agent",
    ]
    implementation_agents = [
        "Repository Understanding Agent",
        "Reproduction Planner Agent",
        "Reproduction Implementation Agent",
    ]
    product_agents = [
        "Reproduction Implementation Agent",
        "Product Evaluator Agent",
    ]

    definitions: list[tuple[ToolSpec, Callable[..., Any]]] = [
        (
            ToolSpec(
                name=name,
                description=description,
                input_schema={"path": "path", "allowed_roots": "list[path]"},
                output_schema={"type": output_type},
                safety_level=safety_level,
                allowed_agents=agents,
            ),
            function,
        )
        for name, description, output_type, safety_level, agents, function in [
            ("list_dir", "List a permitted directory.", "list[string]", "safe", read_agents, list_dir),
            ("tree_view", "Render a bounded project tree.", "object", "safe", read_agents, tree_view),
            ("read_file", "Read a permitted non-secret text file.", "object", "safe", read_agents, read_file),
            ("read_many_files", "Read permitted non-secret text files.", "list[object]", "safe", read_agents, read_many_files),
            ("code_search", "Search project text with line evidence.", "list[object]", "safe", read_agents, code_search),
            ("find_entrypoints", "Find common application entrypoints.", "list[string]", "safe", implementation_agents, find_entrypoints),
            ("find_dataset_paths", "Find dataset-related references.", "list[object]", "safe", implementation_agents, find_dataset_paths),
            ("find_checkpoint_keywords", "Find checkpoint-related references.", "list[object]", "safe", implementation_agents, find_checkpoint_keywords),
            ("find_todo_or_missing", "Find incomplete implementation markers.", "list[object]", "safe", implementation_agents, find_todo_or_missing),
            ("python_ast_summary", "Summarize Python declarations and imports.", "object", "safe", implementation_agents, python_ast_summary),
            ("extract_functions_classes", "Extract Python function and class names.", "object", "safe", implementation_agents, extract_functions_classes),
            ("extract_cli_args", "Extract argparse option declarations.", "list[string]", "safe", implementation_agents, extract_cli_args),
            ("parse_dependency_file", "Parse a supported dependency manifest.", "object", "safe", implementation_agents, parse_dependency_file),
            ("python_syntax_check", "Compile Python source in memory.", "object", "safe", product_agents, python_syntax_check),
            ("compileall_check", "Compile a Python tree in memory.", "object", "safe", product_agents, compileall_check),
            ("pytest_collect", "Collect pytest tests without running test bodies.", "object", "sandbox", product_agents, pytest_collect),
            ("generated_product_inspect", "Inspect a generated product deterministically.", "object", "safe", product_agents, generated_product_inspect),
            ("parse_requirements", "Parse a requirements file.", "object", "safe", implementation_agents, parse_requirements),
            ("parse_pyproject", "Parse project metadata from pyproject.toml.", "object", "safe", implementation_agents, parse_pyproject),
            ("parse_environment_yml", "Parse a Conda environment file.", "object", "safe", implementation_agents, parse_environment_yml),
            ("detect_cuda_requirement", "Detect CUDA-related dependencies.", "boolean", "safe", implementation_agents, detect_cuda_requirement),
            ("detect_python_version", "Detect a declared Python version.", "string", "safe", implementation_agents, detect_python_version),
        ]
    ]
    for spec, function in definitions:
        registry.register(spec, function)
    return registry
