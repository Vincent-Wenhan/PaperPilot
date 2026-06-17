"""Evaluate generated reproduction code against paper evidence."""

from __future__ import annotations

from typing import Any

from agents.structured_agent import StructuredAgent
from schemas.code_review_schema import CodeReview


class CodeReviewAgent(StructuredAgent[CodeReview]):
    """Score generated code for paper fidelity, completeness, correctness, and runnability."""

    def __init__(
        self,
        llm_client=None,
        model: str | None = None,
    ) -> None:
        if llm_client is None and model is None:
            from config import LLM_CODE_REVIEW_MODEL, LLM_MODEL
            model = LLM_CODE_REVIEW_MODEL or LLM_MODEL
        super().__init__(
            name="Code Review Agent",
            prompt_path="code_review_prompt.txt",
            schema_type=CodeReview,
            guideline_names=("reproduction_checklist.md", "code_review_rules.md"),
            llm_client=llm_client,
            model=model,
        )

    def build_mock(self, input_data: dict[str, Any]) -> CodeReview:
        files = list(input_data.get("implementation_bundle", {}).get("files", []))
        has_py_files = any(
            f.get("path", "").endswith(".py") for f in files
        )
        has_readme = any(
            f.get("path", "").lower() == "readme.md" for f in files
        )
        has_requirements = any(
            f.get("path", "").lower() in ("requirements.txt",)
            for f in files
        )

        detected_problems = []
        revision_suggestions = []

        if not has_py_files:
            detected_problems.append("No Python source files generated.")
            revision_suggestions.append("Generate at least one Python module implementing the paper method.")
        if not has_readme:
            detected_problems.append("Missing README.md documentation.")
            revision_suggestions.append("Add a README.md with setup instructions and smoke-test command.")
        if not has_requirements:
            detected_problems.append("Missing requirements.txt.")
            revision_suggestions.append("Declare all Python dependencies in requirements.txt.")

        file_count = len(files)
        if file_count == 0:
            paper_fidelity = 1.0
            completeness = 1.0
            correctness = 1.0
            runnability = 1.0
        elif file_count <= 2:
            paper_fidelity = 2.0
            completeness = 2.0
            correctness = 2.0
            runnability = 2.0 if has_py_files else 1.0
        else:
            paper_fidelity = 3.0
            completeness = 3.0
            correctness = 3.0
            runnability = 3.0 if (has_py_files and has_requirements) else 2.0

        if not detected_problems:
            detected_problems.append("Mock review: no automated analysis performed.")
            revision_suggestions.append("Run a full LLM-based code review for detailed feedback.")

        scores = [paper_fidelity, completeness, correctness, runnability]
        overall_score = round(sum(scores) / len(scores), 2)
        verdict = "accept" if overall_score >= 3.5 else "revise"

        return CodeReview(
            paper_fidelity=paper_fidelity,
            completeness=completeness,
            correctness=correctness,
            runnability=runnability,
            overall_score=overall_score,
            detected_problems=detected_problems,
            revision_suggestions=revision_suggestions,
            verdict=verdict,
        )
