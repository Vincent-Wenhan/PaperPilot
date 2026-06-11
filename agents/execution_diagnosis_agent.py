"""High-level execution result interpretation and diagnosis agent."""

from __future__ import annotations

from typing import Any

from agents.structured_agent import StructuredAgent
from schemas.reproduction_schema import ExecutionDiagnosis
from tools.llm_client import LLMClient


class ExecutionDiagnosisAgent(StructuredAgent[ExecutionDiagnosis]):
    """Interpret deterministic command results without executing commands."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__(
            name="Execution & Diagnosis Agent",
            prompt_path="execution_diagnosis_prompt.txt",
            schema_type=ExecutionDiagnosis,
            guideline_names=("reproduction_checklist.md", "safety_rules.md"),
            llm_client=llm_client,
        )

    def build_mock(self, input_data: dict[str, Any]) -> ExecutionDiagnosis:
        command_results = input_data.get("command_results") or []
        error_log = str(input_data.get("error_log") or "").strip()
        if command_results:
            latest = command_results[-1]
            success = bool(latest.get("success")) or latest.get("exit_code") == 0
            return ExecutionDiagnosis(
                command=str(latest.get("command") or ""),
                executed=bool(latest.get("executed", True)),
                exit_code=latest.get("exit_code", latest.get("returncode")),
                direct_cause=(
                    "The command completed successfully."
                    if success
                    else str(latest.get("stderr") or "The command failed.")
                ),
                possible_root_causes=[] if success else ["Inspect stderr and environment evidence."],
                suggested_fixes=[] if success else ["Verify dependencies, paths, and input assets."],
                next_actions=["Continue with the next reviewed reproduction step."],
                feasibility="feasible" if success else "needs_review",
            )
        if error_log:
            return ExecutionDiagnosis(
                direct_cause="The supplied log requires diagnosis against the actual environment.",
                possible_root_causes=["Dependency, path, configuration, or input mismatch."],
                suggested_fixes=["Verify the first actionable error before changing code."],
                next_actions=["Collect the command, cwd, dependency versions, and full traceback."],
                feasibility="needs_review",
            )
        return ExecutionDiagnosis(
            direct_cause="No reproduction command has been executed.",
            next_actions=["Review and explicitly run only approved command plans."],
            feasibility="planned_not_executed",
        )
