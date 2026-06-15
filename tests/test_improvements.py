"""Tests for integration improvements (stage tracking, cache, runner bridge, retry)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.structured_agent import StructuredAgent
from pipeline.analysis_cache import load_cached_analysis, save_cached_analysis
from pipeline.hitl_retry import rerun_reproduce_stage
from pipeline.output_paths import resolve_output_dir, resolve_output_file
from pipeline.runner_bridge import extract_runner_safe_commands, summarize_planned_commands
from pipeline.stage_tracker import (
    STAGE_FALLBACK,
    STAGE_REAL,
    record_stage_source,
    stage_badge_label,
)
from schemas.reproduction_schema import PaperUnderstanding
from tools.llm_client import LLMClient


class _FlakyLLMClient:
    mock_mode = False
    api_key = "test-key"

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        return self._responses.pop(0)


class _RetryAgent(StructuredAgent[PaperUnderstanding]):
    def __init__(self, responses: list[str]) -> None:
        super().__init__(
            name="Retry Test Agent",
            prompt_path="research_understanding_prompt.txt",
            schema_type=PaperUnderstanding,
            guideline_names=(),
            llm_client=_FlakyLLMClient(responses),  # type: ignore[arg-type]
        )

    def build_mock(self, input_data: dict) -> PaperUnderstanding:
        return PaperUnderstanding(title="mock")


class ImprovementTests(unittest.TestCase):
    def test_resolve_output_dir_uses_paper_name(self) -> None:
        result = {"paper_name": "My_Paper"}
        self.assertTrue(str(resolve_output_dir(result)).endswith("My_Paper"))

    def test_resolve_output_file_joins_paper_subdirectory(self) -> None:
        result = {"paper_name": "demo"}
        path = resolve_output_file(result, "report.md")
        self.assertEqual(path.name, "report.md")
        self.assertEqual(path.parent.name, "demo")

    def test_stage_tracker_records_sources(self) -> None:
        result: dict = {}
        record_stage_source(result, "Research Understanding Agent", STAGE_REAL)
        self.assertEqual(result["stage_sources"]["research"], STAGE_REAL)
        self.assertEqual(stage_badge_label(STAGE_FALLBACK), "Fallback")

    def test_runner_bridge_extracts_safe_commands(self) -> None:
        plans = [
            {"command": "python --version", "purpose": "Check Python", "risk_level": "low"},
            {"command": "pip install torch", "purpose": "Install", "risk_level": "medium"},
        ]
        safe = extract_runner_safe_commands(plans)
        self.assertEqual(len(safe), 1)
        self.assertEqual(safe[0]["command"], "python --version")

    def test_summarize_planned_commands(self) -> None:
        counts = summarize_planned_commands(
            [
                {"command": "python --version", "risk_level": "low"},
                {"command": "pip install x", "risk_level": "medium"},
            ]
        )
        self.assertEqual(counts["low"], 1)
        self.assertEqual(counts["medium"], 1)

    def test_analysis_cache_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(b"%PDF-test-content")
            result = {"paper_info": "cached", "pipeline_status": "complete"}
            with patch("pipeline.analysis_cache.CACHE_DIR", Path(tmp) / "cache"):
                save_cached_analysis(
                    pdf,
                    result,
                    github_url="",
                    hardware="CPU only",
                    gpu_info="",
                    mock_mode=True,
                )
                loaded = load_cached_analysis(
                    pdf,
                    github_url="",
                    hardware="CPU only",
                    gpu_info="",
                    mock_mode=True,
                )
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded["paper_info"], "cached")
            self.assertTrue(loaded.get("_cache_hit"))

    def test_structured_agent_retries_invalid_json_once(self) -> None:
        valid = json.dumps(
            {
                "title": "Retry Paper",
                "task": "Classification",
                "problem": "Test",
                "contributions": ["One"],
                "method_summary": "Summary",
            }
        )
        agent = _RetryAgent(["not json at all", valid])
        parsed = agent.run_structured({"paper_text": "body"})
        self.assertEqual(parsed.title, "Retry Paper")

    def test_hitl_retry_updates_experiment_plan(self) -> None:
        from agents import ReproductionPlannerAgent

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = {
                "paper_text": "paper body",
                "paper_info": "Paper summary",
                "method_info": "Method summary",
                "research_understanding": {"title": "Paper"},
                "repository_understanding": {},
                "execution_diagnosis": {},
                "hardware": "CPU only",
                "gpu_info": "",
                "goal": "run official demo",
                "user_idea": "",
                "errors": [],
            }
            mock_plan = ReproductionPlannerAgent(LLMClient(mock_mode=True)).build_mock(
                {
                    "research_understanding": result["research_understanding"],
                    "repository_understanding": result["repository_understanding"],
                    "hardware": "CPU only",
                    "gpu_info": "",
                    "goal": "run official demo",
                    "user_idea": "",
                }
            )
            with patch.object(
                ReproductionPlannerAgent,
                "run_structured",
                return_value=mock_plan,
            ):
                updated = rerun_reproduce_stage(
                    result,
                    "experiment",
                    "focus on demo commands",
                    llm_client=LLMClient(mock_mode=True),
                    output_dir=output_dir,
                )
            self.assertIn("env_plan", updated)
            self.assertTrue((output_dir / "reproduction_plan.md").is_file())


if __name__ == "__main__":
    unittest.main()
