from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import agents
from tools.llm_client import LLMClient, LLMConnectionError, LLMRequestError


HIGH_LEVEL_AGENTS = {
    "ResearchUnderstandingAgent",
    "RepositoryUnderstandingAgent",
    "ReproductionPlannerAgent",
    "ReproductionImplementationAgent",
    "ExecutionDiagnosisAgent",
    "ResearchSynthesizerAgent",
    "ProductPlannerAgent",
    "PrototypeBuilderAgent",
    "ProductEvaluatorAgent",
}


class FailingLLMClient:
    mock_mode = False
    api_key = "test-key"
    base_url = "https://llm.example.test/v1"
    model = "test-model"

    def __init__(self) -> None:
        self.generate_calls = 0

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        self.generate_calls += 1
        raise LLMConnectionError("Could not connect to test endpoint.")


class UnsupportedImplementationClient:
    mock_mode = False
    api_key = "test-key"
    base_url = "https://llm.example.test/v1"
    model = "unsupported-code-model"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        raise LLMRequestError("code model is not supported")


class AgentArchitectureTests(unittest.TestCase):
    def test_agents_package_exports_only_high_level_agents_and_base(self) -> None:
        self.assertEqual(set(agents.__all__), {"BaseAgent", *HIGH_LEVEL_AGENTS})
        for legacy_name in (
            "PaperReaderAgent",
            "MethodExtractorAgent",
            "RepoAnalyzerAgent",
            "EnvironmentAgent",
            "ExperimentPlannerAgent",
            "RunnerAgent",
            "DebugAgent",
            "ReportAgent",
            "CodeAgent",
        ):
            self.assertFalse(hasattr(agents, legacy_name), legacy_name)

    def test_fragmented_agents_are_not_top_level_files(self) -> None:
        root = Path(agents.__file__).resolve().parent
        expected = {
            "__init__.py",
            "base_agent.py",
            "structured_agent.py",
            "research_understanding_agent.py",
            "repository_understanding_agent.py",
            "reproduction_planner_agent.py",
            "reproduction_implementation_agent.py",
            "execution_diagnosis_agent.py",
            "research_synthesizer_agent.py",
            "product_planner_agent.py",
            "prototype_builder_agent.py",
            "product_evaluator_agent.py",
        }
        self.assertEqual({path.name for path in root.glob("*.py")}, expected)
        self.assertTrue((root / "legacy").is_dir())

    def test_active_code_does_not_import_legacy_agents(self) -> None:
        project_root = Path(agents.__file__).resolve().parent.parent
        active_paths = [
            project_root / "app.py",
            project_root / "main.py",
            *project_root.joinpath("pipeline").glob("*.py"),
            *project_root.joinpath("productize").glob("*.py"),
            *(
                path
                for path in project_root.joinpath("agents").glob("*.py")
                if path.name != "__init__.py"
            ),
        ]
        for path in active_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("agents.legacy", text)

    def test_high_level_reproduce_agents_return_structured_mock_outputs(self) -> None:
        client = LLMClient(mock_mode=True)
        research = agents.ResearchUnderstandingAgent(client).run_structured(
            {"paper_text": "A paper about image classification."}
        )
        repository = agents.RepositoryUnderstandingAgent(client).run_structured(
            {"research_understanding": research.model_dump(), "repo_scan": {}}
        )
        plan = agents.ReproductionPlannerAgent(client).run_structured(
            {
                "research_understanding": research.model_dump(),
                "repository_understanding": repository.model_dump(),
                "goal": "minimal training experiment",
                "hardware": "CPU only",
            }
        )
        implementation = agents.ReproductionImplementationAgent(client).run_structured(
            {
                "research_understanding": research.model_dump(),
                "repository_understanding": repository.model_dump(),
                "reproduction_plan": plan.model_dump(),
            }
        )
        diagnosis = agents.ExecutionDiagnosisAgent(client).run_structured(
            {"command_results": [], "reproduction_plan": plan.model_dump()}
        )
        self.assertTrue(research.method_modules)
        self.assertIn("LLM not called", research.title)
        self.assertEqual(repository.repo_source, "paper-only")
        self.assertTrue(plan.minimal_reproduction_steps)
        self.assertTrue(implementation.files)
        self.assertEqual(diagnosis.feasibility, "planned_not_executed")

    def test_active_pipeline_generates_code_with_high_level_agents(self) -> None:
        from pipeline.reproduce_pipeline import run_reproduce_pipeline

        with (
            patch("pipeline.reproduce_pipeline.parse_pdf", return_value="paper text"),
            patch("pipeline.reproduce_pipeline.save_output"),
            patch(
                "pipeline.reproduce_pipeline.materialize_implementation",
                return_value={
                    "repo_path": "/tmp/generated",
                    "files": ["README.md", "main.py"],
                },
            ),
            patch(
                "pipeline.reproduce_pipeline.scan_repo_detailed",
                return_value={"possible_entrypoints": ["main.py"]},
            ),
        ):
            result = run_reproduce_pipeline(
                pdf_path="paper.pdf",
                github_url="",
                llm_client=LLMClient(model="main-model", mock_mode=True),
                implementation_model="code-model",
            )

        self.assertEqual(result["repo_source"], "Generated reproduction")
        self.assertEqual(result["repo_path"], "/tmp/generated")
        self.assertEqual(result["generated_repo_path"], "/tmp/generated")
        self.assertTrue(result["implementation_bundle"])
        self.assertEqual(result["implementation_model"], "code-model")
        self.assertIn("Generated Reproduction Implementation", result["code_info"])
        self.assertTrue(result["research_understanding"])
        self.assertTrue(result["repository_understanding"])
        self.assertTrue(result["reproduction_plan"])
        self.assertTrue(result["execution_diagnosis"])
        self.assertEqual(result["paper_context"]["characters"], len("paper text"))
        self.assertTrue(any("Mock Mode is enabled" in error for error in result["errors"]))

    def test_pipeline_retries_main_model_when_dedicated_code_model_fails(self) -> None:
        from pipeline.reproduce_pipeline import run_reproduce_pipeline

        progress: list[str] = []
        with (
            patch("pipeline.reproduce_pipeline.parse_pdf", return_value="paper text"),
            patch("pipeline.reproduce_pipeline.save_output"),
            patch(
                "pipeline.reproduce_pipeline.LLMClient",
                return_value=UnsupportedImplementationClient(),
            ),
            patch(
                "pipeline.reproduce_pipeline.materialize_implementation",
                return_value={
                    "repo_path": "/tmp/generated",
                    "files": ["README.md", "main.py"],
                },
            ),
            patch(
                "pipeline.reproduce_pipeline.scan_repo_detailed",
                return_value={"possible_entrypoints": ["main.py"]},
            ),
        ):
            result = run_reproduce_pipeline(
                pdf_path="paper.pdf",
                llm_client=LLMClient(model="main-model", mock_mode=True),
                implementation_model="unsupported-code-model",
                progress_callback=progress.append,
            )

        self.assertEqual(result["implementation_model"], "main-model")
        self.assertTrue(
            any("retrying code generation with main model" in item for item in progress)
        )
        self.assertTrue(
            any("code model is not supported" in error for error in result["errors"])
        )
        self.assertTrue(
            any("Main model retry `main-model` succeeded" in error for error in result["errors"])
        )

    def test_active_pipeline_generates_dry_run_downloader_from_paper_link(self) -> None:
        from pipeline.reproduce_pipeline import run_reproduce_pipeline
        from tools.code_writer import materialize_implementation

        paper = (
            "[Page 1]\nA paper.\n"
            "[Page 2]\nDownload the evaluation dataset from "
            "https://example.com/releases/eval-data.zip before evaluation."
        )
        with TemporaryDirectory() as temp_dir:
            with (
                patch("pipeline.reproduce_pipeline.parse_pdf", return_value=paper),
                patch("pipeline.reproduce_pipeline.save_output"),
                patch(
                    "pipeline.reproduce_pipeline.materialize_implementation",
                    side_effect=lambda bundle: materialize_implementation(bundle, temp_dir),
                ),
            ):
                result = run_reproduce_pipeline(
                    pdf_path="paper.pdf",
                    llm_client=LLMClient(mock_mode=True),
                )

            generated_root = Path(result["generated_repo_path"])
            download_script = generated_root / "scripts" / "download_data.py"
            dry_run = subprocess.run(
                [sys.executable, str(download_script)],
                cwd=generated_root,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            self.assertTrue(download_script.is_file())
            self.assertEqual(dry_run.returncode, 0)
            self.assertIn("https://example.com/releases/eval-data.zip", dry_run.stdout)
            self.assertIn(
                "python scripts/download_data.py --execute",
                result["run_sh"],
            )
            self.assertFalse(
                any("Generated Code Writer" in error for error in result["errors"])
            )

    def test_active_pipeline_fails_fast_when_llm_is_unavailable(self) -> None:
        from pipeline.reproduce_pipeline import run_reproduce_pipeline

        client = FailingLLMClient()
        with (
            patch("pipeline.reproduce_pipeline.parse_pdf", return_value="paper text"),
            patch("pipeline.reproduce_pipeline.save_output"),
        ):
            result = run_reproduce_pipeline(
                pdf_path="paper.pdf",
                llm_client=client,
                generate_code=False,
            )

        self.assertEqual(client.generate_calls, 1)
        self.assertEqual(result["pipeline_status"], "failed")
        self.assertEqual(result["llm_attempts"], 1)
        self.assertEqual(result["llm_failures"], 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("same endpoint and model", result["errors"][0])
        self.assertNotIn("invalid structured output", result["errors"][0])

    def test_llm_failure_is_isolated_by_endpoint_and_model(self) -> None:
        from pipeline.reproduce_pipeline import _run_structured_stage

        result = {
            "errors": [],
            "llm_attempts": 0,
            "llm_failures": 0,
            "llm_unavailable_clients": [],
        }
        failing_client = FailingLLMClient()
        main_client = FailingLLMClient()
        main_client.model = "main-model"

        class FailingAgent:
            def run_structured(self, input_data: dict[str, object]) -> str:
                del input_data
                raise LLMConnectionError("code model unavailable")

        class SuccessfulAgent:
            def run_structured(self, input_data: dict[str, object]) -> str:
                del input_data
                return "diagnosis completed"

        implementation = _run_structured_stage(
            result,
            "Implementation",
            lambda client: FailingAgent(),
            failing_client,
            {"input": "value"},
            fallback=lambda: "implementation fallback",
        )
        diagnosis = _run_structured_stage(
            result,
            "Diagnosis",
            lambda client: SuccessfulAgent(),
            main_client,
            {"input": "value"},
            fallback=lambda: "diagnosis fallback",
        )

        self.assertEqual(implementation, "implementation fallback")
        self.assertEqual(diagnosis, "diagnosis completed")
        self.assertEqual(result["llm_attempts"], 2)

    def test_stage_specific_bad_request_does_not_skip_later_stage(self) -> None:
        from pipeline.reproduce_pipeline import _run_structured_stage

        result = {
            "errors": [],
            "llm_attempts": 0,
            "llm_failures": 0,
            "llm_unavailable_clients": [],
        }
        client = FailingLLMClient()

        class BadRequestAgent:
            def run_structured(self, input_data: dict[str, object]) -> str:
                del input_data
                raise LLMRequestError("HTTP 400 for this stage")

        class SuccessfulAgent:
            def run_structured(self, input_data: dict[str, object]) -> str:
                del input_data
                return "later stage completed"

        _run_structured_stage(
            result,
            "Implementation",
            lambda current: BadRequestAgent(),
            client,
            {"input": "value"},
            fallback=lambda: "implementation fallback",
        )
        later = _run_structured_stage(
            result,
            "Diagnosis",
            lambda current: SuccessfulAgent(),
            client,
            {"input": "value"},
            fallback=lambda: "diagnosis fallback",
        )

        self.assertEqual(later, "later stage completed")
        self.assertEqual(result["llm_attempts"], 2)
        self.assertEqual(result["llm_unavailable_clients"], [])
        self.assertIn("later stages will continue", result["errors"][0])


if __name__ == "__main__":
    unittest.main()
