"""High-level repository and environment-evidence understanding agent."""

from __future__ import annotations

from typing import Any

from agents.structured_agent import StructuredAgent
from schemas.reproduction_schema import RepositoryUnderstanding, ResourceLink
from tools.llm_client import LLMClient


def _entrypoints(repo_scan: dict[str, Any], keywords: tuple[str, ...]) -> list[str]:
    return [
        item
        for item in repo_scan.get("possible_entrypoints", [])
        if any(keyword in item.lower() for keyword in keywords)
    ]


class RepositoryUnderstandingAgent(StructuredAgent[RepositoryUnderstanding]):
    """Merge repository analysis and environment evidence into one stage."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Repository Understanding Agent",
            prompt_path="repository_understanding_prompt.txt",
            schema_type=RepositoryUnderstanding,
            guideline_names=("reproduction_checklist.md", "safety_rules.md"),
            llm_client=llm_client,
        )

    def build_mock(self, input_data: dict[str, Any]) -> RepositoryUnderstanding:
        scan = input_data.get("repo_scan") or {}
        if not scan:
            return RepositoryUnderstanding(
                repo_source="paper-only",
                notes=[
                    "No repository was provided; repository-specific claims remain unknown."
                ],
                risk_signals=["missing_repository_evidence"],
            )
        possible = list(scan.get("possible_entrypoints", []))
        dependencies = list(scan.get("dependency_files", []))
        if not dependencies:
            dependencies = [
                item
                for item in scan.get("important_files", [])
                if item in {"requirements.txt", "environment.yml", "pyproject.toml"}
            ]
        return RepositoryUnderstanding(
            repo_source=str(scan.get("repository_source") or "GitHub repository"),
            repo_url=str(input_data.get("github_url") or ""),
            repo_path=str(scan.get("repo_path") or ""),
            detected_framework=str(scan.get("detected_framework") or "unknown"),
            dependency_files=dependencies,
            config_files=list(scan.get("config_files", [])),
            training_entrypoints=_entrypoints(scan, ("train",)),
            evaluation_entrypoints=_entrypoints(scan, ("eval", "test")),
            demo_entrypoints=_entrypoints(
                scan,
                ("demo", "app", "infer", "main", "generate", "predict"),
            ),
            resource_links=[
                ResourceLink.model_validate(item)
                for item in scan.get("resource_links", [])
            ],
            risk_signals=list(scan.get("risk_signals", [])),
            minimal_runnable_candidates=possible[:5],
            environment_evidence=list(scan.get("notes", [])),
            notes=["Repository evidence was gathered by deterministic static scanning."],
        )
