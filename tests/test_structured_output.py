"""Tests for the active high-level structured agents and renderers."""

from __future__ import annotations

import json
import unittest

from agents import (
    ReproductionImplementationAgent,
    ResearchUnderstandingAgent,
    RepositoryUnderstandingAgent,
)
from agents.base_agent import BaseAgent
from pipeline.productize_renderers import render_opportunities
from pipeline.reproduce_renderers import (
    render_method_breakdown,
    render_repository_understanding,
    render_research_summary,
)
from schemas.product_schema import ProductOpportunity, ProductOpportunityList
from schemas.reproduction_schema import PaperUnderstanding
from tools.llm_client import LLMConnectionError


class MockLLMClient:
    mock_mode = False

    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(self.response)


class FailingLLMClient:
    mock_mode = False

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        raise LLMConnectionError("Could not connect to test endpoint.")


class StructuredOutputTests(unittest.TestCase):
    def test_lenient_json_parser_repairs_unescaped_control_characters(self) -> None:
        raw = '{"title":"Test Paper","method_summary":"line one\nline two\tend"}'

        model, error = BaseAgent.repair_json_output(raw, PaperUnderstanding)

        self.assertIsNone(error)
        self.assertIsNotNone(model)
        self.assertEqual(model.method_summary, "line one\nline two\tend")

    def test_research_understanding_parses_real_json(self) -> None:
        agent = ResearchUnderstandingAgent(
            MockLLMClient(
                {
                    "title": "Test Paper",
                    "task": "Classification",
                    "problem": "Classify test inputs.",
                    "contributions": ["A test contribution."],
                    "method_summary": "A test method.",
                    "method_modules": [
                        {
                            "name": "encoder",
                            "purpose": "Encode inputs.",
                            "inputs": ["input tensor"],
                            "outputs": ["latent tensor"],
                            "mechanism": ["Apply an encoder."],
                            "evidence": ["[Page 2] The encoder processes inputs."],
                        },
                        {
                            "name": "classifier",
                            "purpose": "Predict labels.",
                            "inputs": ["latent tensor"],
                            "outputs": ["label logits"],
                            "mechanism": ["Apply a classifier."],
                            "evidence": ["[Page 3] The classifier predicts labels."],
                        },
                    ],
                    "end_to_end_dataflow": ["Input -> encoder -> classifier"],
                    "implementation_blueprint": ["Implement encoder and classifier modules."],
                    "evidence": ["[Page 2] The encoder processes inputs."],
                }
            )
        )
        model = agent.run_structured({"paper_text": "paper"})
        self.assertEqual(model.title, "Test Paper")
        self.assertIn("encoder", render_method_breakdown(model))
        self.assertIn("Classification", render_research_summary(model))

    def test_research_understanding_rejects_empty_valid_json(self) -> None:
        agent = ResearchUnderstandingAgent(MockLLMClient({}))
        with self.assertRaisesRegex(RuntimeError, "missing core paper fields"):
            agent.run_structured({"paper_text": "paper"})

    def test_research_understanding_preserves_connection_error(self) -> None:
        agent = ResearchUnderstandingAgent(FailingLLMClient())

        with self.assertRaisesRegex(LLMConnectionError, "test endpoint"):
            agent.run_structured({"paper_text": "paper"})

    def test_research_understanding_requires_page_specific_evidence(self) -> None:
        agent = ResearchUnderstandingAgent(
            MockLLMClient(
                {
                    "title": "Test Paper",
                    "task": "Classification",
                    "problem": "Classify test inputs.",
                    "contributions": ["A test contribution."],
                    "method_summary": "A test method.",
                    "method_modules": [
                        {
                            "name": "encoder",
                            "purpose": "Encode inputs.",
                            "inputs": ["input"],
                            "outputs": ["latent"],
                            "mechanism": ["Encode."],
                            "evidence": ["[Page 1] Encode inputs."],
                        }
                    ],
                    "end_to_end_dataflow": ["Input -> encoder"],
                    "implementation_blueprint": ["Implement encoder."],
                    "evidence": ["The encoder processes inputs."],
                }
            )
        )
        with self.assertRaisesRegex(RuntimeError, r"\[Page N\]"):
            agent.run_structured({"paper_text": "[Page 1] paper"})

    def test_repository_understanding_parses_real_json(self) -> None:
        agent = RepositoryUnderstandingAgent(
            MockLLMClient(
                {
                    "repo_source": "GitHub repository",
                    "repo_path": "/tmp/repo",
                    "detected_framework": "pytorch",
                    "training_entrypoints": ["train.py"],
                }
            )
        )
        model = agent.run_structured({"repo_scan": {"repo_path": "/tmp/repo"}})
        self.assertEqual(model.detected_framework, "pytorch")
        self.assertIn("GitHub repository", render_repository_understanding(model))

    def test_reproduction_implementation_parses_complete_code_bundle(self) -> None:
        agent = ReproductionImplementationAgent(
            MockLLMClient(
                {
                    "project_name": "demo",
                    "summary": "A minimal implementation.",
                    "fidelity_scope": ["One vertical slice."],
                    "assumptions": ["Synthetic data."],
                    "files": [
                        {
                            "path": "README.md",
                            "purpose": "Documentation",
                            "content": "# Demo\n",
                        },
                        {
                            "path": "main.py",
                            "purpose": "Entry point",
                            "content": "print('ok')\n",
                        },
                        {
                            "path": "tests/test_smoke.py",
                            "purpose": "Smoke test",
                            "content": "def test_smoke(): assert True\n",
                        },
                    ],
                    "smoke_test_command": "python main.py",
                }
            )
        )
        bundle = agent.run_structured({"reproduction_plan": {}})
        self.assertEqual(bundle.project_name, "demo")
        self.assertEqual(len(bundle.files), 3)

    def test_reproduction_implementation_adds_missing_required_scaffold(self) -> None:
        agent = ReproductionImplementationAgent(
            MockLLMClient(
                {
                    "project_name": "lpwm",
                    "summary": "A model-generated LPWM approximation.",
                    "files": [
                        {
                            "path": "lpwm/model.py",
                            "purpose": "",
                            "content": "class Model: pass\n",
                        }
                    ],
                    "smoke_test_command": "",
                }
            )
        )

        bundle = agent.run_structured({"reproduction_plan": {}})
        paths = {item.path for item in bundle.files}

        self.assertIn("lpwm/model.py", paths)
        self.assertIn("README.md", paths)
        self.assertIn("main.py", paths)
        self.assertIn("tests/test_generated_project.py", paths)
        self.assertEqual(bundle.smoke_test_command, "python main.py --smoke-test")
        self.assertTrue(all(item.purpose for item in bundle.files))

    def test_reproduction_implementation_injects_approved_download_urls(self) -> None:
        response = {
            "project_name": "demo",
            "summary": "A minimal implementation with data preparation.",
            "data_resources": [],
            "files": [
                {"path": "README.md", "purpose": "Docs", "content": "# Demo\n"},
                {"path": "main.py", "purpose": "Entry point", "content": "print('ok')\n"},
                {
                    "path": "tests/test_smoke.py",
                    "purpose": "Smoke test",
                    "content": "def test_smoke(): assert True\n",
                },
            ],
            "data_download_command": "",
            "smoke_test_command": "python main.py",
        }
        approved = [
            {
                "name": "data.zip",
                "url": "https://example.com/data.zip",
                "destination": "data/data.zip",
                "source": "paper PDF",
                "evidence": "[Page 4] Download dataset.",
            }
        ]
        agent = ReproductionImplementationAgent(MockLLMClient(response))

        bundle = agent.run_structured(
            {"reproduction_plan": {}, "approved_resource_links": approved}
        )

        self.assertEqual(bundle.data_resources[0].url, approved[0]["url"])
        self.assertEqual(bundle.data_download_command, "python scripts/download_data.py --execute")
        download_file = next(
            item for item in bundle.files if item.path == "scripts/download_data.py"
        )
        self.assertIn(approved[0]["url"], download_file.content)
        self.assertIn("--execute", download_file.content)

    def test_reproduction_implementation_strips_unapproved_download_urls(self) -> None:
        agent = ReproductionImplementationAgent(
            MockLLMClient(
                {
                    "summary": "A minimal implementation.",
                    "data_resources": [
                        {
                            "url": "https://example.com/unapproved.zip",
                            "destination": "data/unapproved.zip",
                        }
                    ],
                    "files": [
                        {"path": "README.md", "purpose": "Docs", "content": "# Demo\n"},
                        {"path": "main.py", "purpose": "Entry point", "content": "print('ok')\n"},
                        {
                            "path": "tests/test_smoke.py",
                            "purpose": "Smoke test",
                            "content": "def test_smoke(): assert True\n",
                        },
                        {
                            "path": "scripts/download_data.py",
                            "purpose": "Downloader",
                            "content": "print('download')\n",
                        },
                    ],
                    "data_download_command": "python scripts/download_data.py --execute",
                    "smoke_test_command": "python main.py",
                }
            )
        )

        bundle = agent.run_structured(
            {"reproduction_plan": {}, "approved_resource_links": []}
        )

        self.assertEqual(bundle.data_resources, [])
        self.assertEqual(bundle.data_download_command, "")
        self.assertFalse(
            any(item.path == "scripts/download_data.py" for item in bundle.files)
        )

    def test_product_opportunity_renderer(self) -> None:
        model = ProductOpportunityList(
            opportunities=[
                ProductOpportunity(
                    idea_name="Research Workbench",
                    target_user="Students",
                    core_value="Explain methods",
                    technical_feasibility=5,
                    demo_feasibility=5,
                    model_availability=3,
                    data_requirement=5,
                    integration_risk=2,
                    user_value=4,
                    course_presentation_value=5,
                    overall_score=4.4,
                    reason="Bounded and clear.",
                )
            ]
        )
        rendered = render_opportunities(model)
        self.assertIn("Research Workbench", rendered)
        self.assertIn("4.4/5", rendered)


if __name__ == "__main__":
    unittest.main()
