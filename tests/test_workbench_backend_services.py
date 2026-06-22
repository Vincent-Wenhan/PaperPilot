from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.schemas import (
    ActionEditRequest,
    ActionRequest,
    CommandReviewRequest,
    PatchProposeRequest,
    RunCreateRequest,
    RunRecord,
    SyntaxCheckRequest,
    WorkbenchEvent,
)
from backend.services.artifact_service import ArtifactService
from backend.services.check_service import CheckService
from backend.services.command_service import CommandService
from backend.services.file_service import FileService
from backend.services.graph_service import graph_service
from backend.services.patch_service import PatchService
from backend.services.run_service import InMemoryRunService, PRODUCTIZE_PLAN, REPRODUCE_PLAN
from backend.services.workbench_mock import build_workbench_snapshot, utc_now
from config import WORKSPACE_DIR
from schemas.product_schema import ProductOpportunity, ProductProposal, PRD as ProductPRD
from tools.llm_client import LLMClient


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    async def accept(self) -> None:
        return None

    async def send_json(self, payload: dict[str, object]) -> None:
        self.sent.append(payload)


class WorkbenchBackendServiceTests(unittest.TestCase):
    def _product_proposal(self, name: str) -> ProductProposal:
        opportunity = ProductOpportunity(
            idea_name=name,
            target_user="Students",
            core_value="Turn research into a demo",
            technical_feasibility=5,
            demo_feasibility=5,
            model_availability=4,
            data_requirement=4,
            integration_risk=2,
            user_value=4,
            course_presentation_value=5,
            overall_score=4.5,
            reason="Strong mock-first fit.",
        )
        return ProductProposal(
            product_name=name,
            target_user="Students",
            product_goal="Interactive demo",
            jtbd="Help students understand research capabilities.",
            opportunities=[opportunity],
            prd=ProductPRD(
                product_name=name,
                problem_statement="Research papers are hard to evaluate quickly.",
                target_users=["Students"],
                goals=["Create a working demo"],
                core_features=["Upload inputs", "Show mock analysis"],
                user_flow=["Open demo", "Submit input", "Review output"],
            ),
            risks=["Mock output may overstate real readiness."],
        )

    def test_productize_request_accepts_multiple_pdf_paths(self) -> None:
        request = RunCreateRequest(
            mode="productize",
            pdf_paths=["papers/a.pdf", "papers/b.pdf"],
        )

        self.assertEqual(request.pdf_path, "")
        self.assertEqual(request.pdf_paths, ["papers/a.pdf", "papers/b.pdf"])

    def test_productize_input_event_mentions_all_selected_pdf_paths(self) -> None:
        service = InMemoryRunService()
        run = service.create_run(
            RunCreateRequest(
                mode="productize",
                project_id="project_test",
                task="Productize multiple papers",
                pdf_paths=["papers/a.pdf", "papers/b.pdf"],
            )
        )

        input_event = next(
            event for event in service.list_events(run.run_id)
            if event.event_type == "input_received"
        )
        self.assertIn("2 papers", input_event.message)
        self.assertIn("papers/a.pdf", input_event.message)
        self.assertIn("papers/b.pdf", input_event.message)

    def test_file_service_exposes_source_repository_for_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            generated_root = (
                project_root / "workspace" / "runs" / "run_source" / "outputs" / "code"
            )
            source_repo = project_root / "workspace" / "taldatech__lpwm"
            generated_root.mkdir(parents=True)
            source_repo.mkdir(parents=True)
            (generated_root / "main.py").write_text("print('generated')\n", encoding="utf-8")
            (source_repo / "README.md").write_text("# source repo\n", encoding="utf-8")

            fake_run_service = SimpleNamespace(
                get_run=lambda _run_id: SimpleNamespace(
                    result_summary={"generated_code_output_dir": str(generated_root)}
                ),
                get_result=lambda _run_id: {
                    "repository_understanding": {"repo_path": str(source_repo)}
                },
                list_actions=lambda _run_id: [],
            )
            file_service = FileService(project_root=project_root, file_roots=[])

            with patch("backend.services.run_service.run_service", fake_run_service):
                files = file_service.list_files(run_id="run_source")

            paths = {file.path for file in files}
            self.assertIn("workspace/runs/run_source/outputs/code/main.py", paths)
            self.assertIn("workspace/taldatech__lpwm/README.md", paths)

    def test_mock_snapshot_contains_workbench_contracts(self) -> None:
        snapshot = build_workbench_snapshot()

        self.assertEqual(snapshot.project_id, "project_demo")
        self.assertEqual(snapshot.active_run.status, "waiting_review")
        self.assertTrue(snapshot.events)
        self.assertTrue(snapshot.actions)
        self.assertTrue(snapshot.artifacts)
        self.assertIn("Review medium-risk", " ".join(snapshot.active_run.plan))

    def test_run_service_tracks_events_and_action_decisions(self) -> None:
        service = InMemoryRunService()
        run = service.create_run(
            RunCreateRequest(
                mode="reproduce",
                project_id="project_test",
                task="Reproduce with bounded runner",
                pdf_path="papers/custom.pdf",
                github_url="https://github.com/example/custom-paper",
            )
        )

        self.assertEqual(run.project_id, "project_test")
        self.assertEqual(run.mode, "reproduce")
        self.assertEqual(run.inputs["pdf_path"], "papers/custom.pdf")
        self.assertEqual(
            run.inputs["github_url"],
            "https://github.com/example/custom-paper",
        )
        self.assertNotIn("api_key", run.inputs)
        events = service.list_events(run.run_id)
        self.assertGreater(len(events), 0)
        self.assertIn("papers/custom.pdf", " ".join(event.message for event in events))
        self.assertNotIn("train.py, eval.py", " ".join(event.message for event in events))
        self.assertEqual(service.list_actions(run.run_id), [])

    def test_run_service_can_execute_reproduce_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4 mock paper")
            service = InMemoryRunService()
            request = RunCreateRequest(
                mode="reproduce",
                project_id="project_agents",
                task="Run the existing reproduce agents",
                pdf_path=str(pdf),
                api_key="secret-key",
                mock_mode=True,
                run_pipeline=False,
            )
            run = service.create_run(request)

            with patch.object(
                InMemoryRunService,
                "_execute_reproduce",
                return_value={
                    "pipeline_status": "complete",
                    "paper_info": "paper",
                    "method_info": "method",
                    "report": "report",
                    "run_sh": "run",
                    "generated_files": [{"path": "main.py"}],
                    "errors": [],
                    "llm_attempts": 0,
                    "llm_failures": 0,
                },
            ) as mocked_pipeline:
                completed = service.run_pipeline_now(run.run_id, request)

            self.assertIsNotNone(completed)
            self.assertEqual(completed.status, "success")
            mocked_pipeline.assert_called_once()
            self.assertEqual(mocked_pipeline.call_args.args[0], run.run_id)
            self.assertEqual(str(mocked_pipeline.call_args.args[1]), str(pdf))
            self.assertNotIn("secret-key", str(service.list_events(run.run_id)))
            self.assertEqual(
                service.get_result(run.run_id)["pipeline_status"],
                "complete",
            )

    def test_run_service_recovers_failed_status_from_terminal_event(self) -> None:
        service = InMemoryRunService()
        run_id = "run_stale_failed"
        started = utc_now()
        service._runs[run_id] = RunRecord(
            run_id=run_id,
            project_id="project_agents",
            mode="reproduce",
            status="running",
            task="stale run",
            created_at=started,
            updated_at=started,
            summary="Reproduce agent workflow is running.",
            inputs={"pdf_path": "paper.pdf"},
            plan=REPRODUCE_PLAN,
        )
        events = [
            WorkbenchEvent(
                event_id="evt_start",
                run_id=run_id,
                node="agent_runtime",
                agent="Workbench Runner",
                event_type="pipeline_started",
                status="running",
                message="Starting PaperPilot agent pipeline.",
                payload={},
                created_at=started,
            ),
            WorkbenchEvent(
                event_id="evt_failed",
                run_id=run_id,
                node="agent_runtime",
                agent="Workbench Runner",
                event_type="pipeline_failed",
                status="failed",
                message="Agent pipeline failed: No space left on device",
                payload={
                    "pipeline_status": "failed",
                    "errors": ["No space left on device"],
                },
                created_at=utc_now(),
            ),
        ]

        service._recover_terminal_status_from_events(run_id, events)

        recovered = service.get_run(run_id)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.status, "failed")
        self.assertEqual(recovered.result_summary["pipeline_status"], "failed")
        self.assertIn("No space", recovered.summary)

    def test_run_service_recovers_failed_status_from_stored_result(self) -> None:
        service = InMemoryRunService()
        run_id = "run_stale_result_failed"
        started = utc_now()
        service._runs[run_id] = RunRecord(
            run_id=run_id,
            project_id="project_agents",
            mode="reproduce",
            status="running",
            task="stale run",
            created_at=started,
            updated_at=started,
            summary="Reproduce agent workflow is running.",
            inputs={"pdf_path": "paper.pdf"},
            plan=REPRODUCE_PLAN,
        )
        service._results[run_id] = {
            "pipeline_status": "failed",
            "errors": ["No space left on device"],
        }

        service._recover_terminal_status_from_results()

        recovered = service.get_run(run_id)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.status, "failed")
        self.assertEqual(recovered.result_summary["pipeline_status"], "failed")
        self.assertIn("No space", recovered.summary)

    def test_run_service_marks_orphan_running_run_failed_on_startup(self) -> None:
        service = InMemoryRunService()
        run_id = "run_orphan_running"
        started = utc_now()
        service._runs[run_id] = RunRecord(
            run_id=run_id,
            project_id="project_agents",
            mode="reproduce",
            status="running",
            task="orphan run",
            created_at=started,
            updated_at=started,
            summary="Reproduce agent workflow is running.",
            inputs={"pdf_path": "paper.pdf"},
            plan=REPRODUCE_PLAN,
        )

        service._recover_stale_running_runs()

        recovered = service.get_run(run_id)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.status, "failed")
        self.assertEqual(recovered.result_summary["pipeline_status"], "failed")
        self.assertIn("interrupted", recovered.summary)

    def test_run_service_uses_run_scoped_workspace_output_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4 mock paper")
            service = InMemoryRunService()

            reproduce_request = RunCreateRequest(
                mode="reproduce",
                project_id="project_agents",
                task="Run scoped reproduce",
                pdf_path=str(pdf),
                mock_mode=True,
                run_pipeline=False,
            )
            reproduce_run = service.create_run(reproduce_request)
            with patch("main.run_paperpilot") as run_paperpilot:
                run_paperpilot.return_value = {"pipeline_status": "complete", "errors": []}
                service._execute_reproduce(
                    reproduce_run.run_id,
                    pdf,
                    reproduce_request,
                    LLMClient(mock_mode=True),
                    lambda stage: None,
                )
            self.assertEqual(
                run_paperpilot.call_args.kwargs["output_dir"],
                WORKSPACE_DIR / "runs" / reproduce_run.run_id / "outputs",
            )

            product_request = RunCreateRequest(
                mode="productize",
                project_id="project_agents",
                task="Run scoped productize",
                pdf_path=str(pdf),
                mock_mode=True,
                run_pipeline=False,
            )
            product_run = service.create_run(product_request)
            proposal = self._product_proposal("Scoped Proposal")
            with (
                patch("main.run_paperpilot") as analyze,
                patch("pipeline.productize_pipeline.generate_proposals") as generate,
            ):
                analyze.return_value = {
                    "paper_info": "paper",
                    "method_info": "method",
                    "repo_info": "",
                    "repo_path": "",
                    "errors": [],
                }
                generate.return_value = (
                    [proposal],
                    {
                        "pipeline_status": "complete",
                        "research_synthesis": {"capability_cards": []},
                        "errors": [],
                    },
                )
                product_result = service._execute_productize(
                    product_run.run_id,
                    pdf,
                    product_request,
                    LLMClient(mock_mode=True),
                    lambda stage: None,
                )
            self.assertEqual(product_result["productize_stage"], "proposal_review")
            self.assertEqual(generate.call_args.kwargs["papers"][0]["title"], "paper")

    def test_productize_generates_reviewable_proposals_for_multiple_papers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first_pdf = Path(tmp) / "first.pdf"
            second_pdf = Path(tmp) / "second.pdf"
            first_pdf.write_bytes(b"%PDF-1.4 first")
            second_pdf.write_bytes(b"%PDF-1.4 second")
            service = InMemoryRunService()
            request = RunCreateRequest(
                mode="productize",
                project_id="project_agents",
                task="Build a product from two papers",
                pdf_paths=[str(first_pdf), str(second_pdf)],
                mock_mode=True,
                run_pipeline=False,
            )
            run = service.create_run(request)
            proposals = [
                self._product_proposal("Proposal A"),
                self._product_proposal("Proposal B"),
                self._product_proposal("Proposal C"),
                self._product_proposal("Proposal D"),
            ]

            with (
                patch("main.run_paperpilot") as analyze,
                patch("pipeline.productize_pipeline.generate_proposals") as generate,
            ):
                analyze.side_effect = [
                    {
                        "paper_info": "paper one",
                        "method_info": "method one",
                        "repo_info": "repo one",
                        "repo_path": "/tmp/repo-one",
                        "errors": [],
                    },
                    {
                        "paper_info": "paper two",
                        "method_info": "method two",
                        "repo_info": "repo two",
                        "repo_path": "/tmp/repo-two",
                        "errors": [],
                    },
                ]
                generate.return_value = (
                    proposals,
                    {
                        "pipeline_status": "complete",
                        "research_synthesis": {"capability_cards": []},
                        "errors": [],
                        "llm_attempts": 0,
                        "llm_failures": 0,
                    },
                )
                result = service._execute_productize(
                    run.run_id,
                    first_pdf,
                    request,
                    LLMClient(mock_mode=True),
                    lambda stage: None,
                )

            self.assertEqual(analyze.call_count, 2)
            passed_papers = generate.call_args.kwargs["papers"]
            self.assertEqual([paper["title"] for paper in passed_papers], ["first", "second"])
            self.assertEqual(result["productize_stage"], "proposal_review")
            self.assertEqual(len(result["productize_proposals"]), 3)
            self.assertEqual(result["productize_proposals"][1]["product_name"], "Proposal B")
            self.assertEqual(result["papers"][1]["paper_info"], "paper two")

    def test_productize_continues_to_proposal_review_when_paper_analysis_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4 paper")
            service = InMemoryRunService()
            request = RunCreateRequest(
                mode="productize",
                project_id="project_agents",
                task="Build a product despite analysis failure",
                pdf_path=str(pdf),
                mock_mode=True,
                run_pipeline=False,
            )
            run = service.create_run(request)
            proposal = self._product_proposal("Fallback Proposal")

            with (
                patch("main.run_paperpilot") as analyze,
                patch("pipeline.productize_pipeline.generate_proposals") as generate,
            ):
                analyze.side_effect = RuntimeError(
                    "cannot schedule new futures after interpreter shutdown"
                )
                generate.return_value = (
                    [proposal],
                    {
                        "pipeline_status": "complete",
                        "research_synthesis": {"capability_cards": []},
                        "errors": [],
                    },
                )
                result = service._execute_productize(
                    run.run_id,
                    pdf,
                    request,
                    LLMClient(mock_mode=True),
                    lambda stage: None,
                )

            self.assertEqual(result["productize_stage"], "proposal_review")
            self.assertEqual(len(result["productize_proposals"]), 1)
            self.assertIn("analysis failed", result["papers"][0]["paper_info"].lower())
            self.assertTrue(result["source_analysis"][0]["errors"])
            self.assertTrue(generate.call_args.kwargs["papers"][0]["errors"])

    def test_productize_proposal_review_summary_points_to_next_action(self) -> None:
        summary = InMemoryRunService._summary_from_result(
            RunCreateRequest(mode="productize"),
            {"pipeline_status": "proposal_review"},
            "waiting_review",
        )

        self.assertEqual(summary, "Product proposals are ready; choose one to scaffold.")

    def test_productize_proposal_review_summary_is_normalized_for_existing_runs(self) -> None:
        service = InMemoryRunService()
        run_id = "run_productize_old_summary"
        started = utc_now()
        service._runs[run_id] = RunRecord(
            run_id=run_id,
            project_id="project_agents",
            mode="productize",
            status="waiting_review",
            task="Productize",
            created_at=started,
            updated_at=started,
            summary="productize agent pipeline completed with review items.",
            inputs={"pdf_path": "paper.pdf"},
            result_summary={"pipeline_status": "proposal_review"},
            plan=PRODUCTIZE_PLAN,
        )

        service._normalize_productize_proposal_review_runs()

        recovered = service.get_run(run_id)
        self.assertIsNotNone(recovered)
        self.assertEqual(
            recovered.summary,
            "Product proposals are ready; choose one to scaffold.",
        )

    def test_productize_executes_selected_proposal_from_review_state(self) -> None:
        service = InMemoryRunService()
        run = service.create_run(
            RunCreateRequest(
                mode="productize",
                pdf_path=__file__,
                mock_mode=True,
                run_pipeline=False,
            )
        )
        first = self._product_proposal("Proposal A")
        second = self._product_proposal("Proposal B")
        service._store_result(
            run.run_id,
            {
                "pipeline_status": "proposal_review",
                "productize_stage": "proposal_review",
                "productize_proposals": [
                    first.model_dump(mode="json"),
                    second.model_dump(mode="json"),
                ],
                "papers": [
                    {
                        "paper_id": "paper-1",
                        "title": "First",
                        "paper_info": "paper",
                        "method_info": "method",
                        "repo_info": "repo",
                        "repo_path": "/tmp/source",
                    }
                ],
                "research_synthesis": {"capability_cards": []},
                "preferred_type": "text",
                "errors": [],
                "llm_attempts": 0,
                "llm_failures": 0,
            },
        )

        with patch("pipeline.productize_pipeline.execute_proposal") as execute:
            execute.return_value = {
                "pipeline_status": "complete",
                "productize_stage": "executed",
                "selected_proposal": second.model_dump(mode="json"),
                "scaffold_result": {"output_dir": "workspace/runs/run/generated_product"},
                "errors": [],
            }
            result = service.execute_productize_proposal(run.run_id, 1)

        self.assertEqual(result["selected_proposal"]["product_name"], "Proposal B")
        self.assertEqual(execute.call_args.kwargs["proposal"].product_name, "Proposal B")
        self.assertEqual(execute.call_args.kwargs["papers"][0]["title"], "First")
        self.assertEqual(
            execute.call_args.kwargs["research_synthesis"],
            {"capability_cards": []},
        )
        self.assertEqual(
            execute.call_args.kwargs["output_dir"],
            WORKSPACE_DIR / "runs" / run.run_id / "generated_product",
        )
        self.assertEqual(service.get_run(run.run_id).status, "success")

    def test_productize_proposal_execution_uses_request_llm_config(self) -> None:
        service = InMemoryRunService()
        run = service.create_run(
            RunCreateRequest(
                mode="productize",
                pdf_path=__file__,
                run_pipeline=False,
            )
        )
        proposal = self._product_proposal("Configured Proposal")
        service._store_result(
            run.run_id,
            {
                "pipeline_status": "proposal_review",
                "productize_stage": "proposal_review",
                "productize_proposals": [proposal.model_dump(mode="json")],
                "papers": [],
                "research_synthesis": {"capability_cards": []},
                "preferred_type": "text",
                "errors": [],
                "llm_attempts": 0,
                "llm_failures": 0,
            },
        )

        with patch("pipeline.productize_pipeline.execute_proposal") as execute:
            execute.return_value = {
                "pipeline_status": "complete",
                "productize_stage": "executed",
                "selected_proposal": proposal.model_dump(mode="json"),
                "errors": [],
            }
            service.execute_productize_proposal(
                run.run_id,
                0,
                api_key="secret-key",
                base_url="https://openrouter.ai/api/v1",
                model="gpt-4o",
                mock_mode=False,
            )

        client = execute.call_args.kwargs["llm_client"]
        self.assertEqual(client.api_key, "secret-key")
        self.assertEqual(client.base_url, "https://openrouter.ai/api/v1")
        self.assertEqual(client.model, "gpt-4o")
        self.assertFalse(client.mock_mode)
        self.assertNotIn("secret-key", str(service.list_events(run.run_id)))

    def test_productize_proposal_execution_reuses_run_scoped_llm_config(self) -> None:
        service = InMemoryRunService()
        run = service.create_run(
            RunCreateRequest(
                mode="productize",
                pdf_path=__file__,
                api_key="secret-key",
                base_url="https://openrouter.ai/api/v1",
                model="gpt-4o",
                mock_mode=False,
                run_pipeline=False,
            )
        )
        proposal = self._product_proposal("Stored Config Proposal")
        service._store_result(
            run.run_id,
            {
                "pipeline_status": "proposal_review",
                "productize_stage": "proposal_review",
                "productize_proposals": [proposal.model_dump(mode="json")],
                "papers": [],
                "research_synthesis": {"capability_cards": []},
                "preferred_type": "text",
                "errors": [],
            },
        )

        with patch("pipeline.productize_pipeline.execute_proposal") as execute:
            execute.return_value = {
                "pipeline_status": "complete",
                "selected_proposal": proposal.model_dump(mode="json"),
                "errors": [],
            }
            service.execute_productize_proposal(run.run_id, 0)

        client = execute.call_args.kwargs["llm_client"]
        self.assertEqual(client.api_key, "secret-key")
        self.assertEqual(client.base_url, "https://openrouter.ai/api/v1")
        self.assertEqual(client.model, "gpt-4o")
        self.assertFalse(client.mock_mode)
        self.assertNotIn("secret-key", str(service.get_run(run.run_id).inputs))
        self.assertNotIn("secret-key", str(service.list_events(run.run_id)))

    def test_pipeline_output_creates_real_command_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4 mock paper")
            service = InMemoryRunService()
            request = RunCreateRequest(
                mode="reproduce",
                project_id="project_agents",
                task="Run generated smoke check",
                pdf_path=str(pdf),
                mock_mode=True,
                run_pipeline=False,
            )
            run = service.create_run(request)

            with patch.object(
                InMemoryRunService,
                "_execute_reproduce",
                return_value={
                    "pipeline_status": "complete",
                    "implementation_bundle": {
                        "smoke_test_command": "python --version",
                    },
                    "generated_files": [{"path": "main.py"}],
                    "errors": [],
                    "llm_attempts": 0,
                    "llm_failures": 0,
                },
            ):
                completed = service.run_pipeline_now(run.run_id, request)

            self.assertIsNotNone(completed)
            self.assertEqual(completed.status, "waiting_review")
            actions = service.list_actions(run.run_id)
            self.assertEqual(len(actions), 1)
            action = actions[0]
            self.assertEqual(action.tool, "run_command")
            self.assertEqual(action.command, "python --version")
            self.assertEqual(action.cwd, ".")
            self.assertEqual(action.execution_mode, "safe")
            self.assertEqual(action.execution_status, "not_started")
            executed = service.execute_action(action.action_id)
            self.assertIsNotNone(executed)
            self.assertEqual(executed.execution_status, "succeeded")
            reviewed = service.get_run(run.run_id)
            self.assertIsNotNone(reviewed)
            self.assertEqual(reviewed.status, "success")
            self.assertEqual(reviewed.result_summary["pending_actions"], 0)
            self.assertTrue(
                any(
                    event.event_type == "review_actions_resolved"
                    for event in service.list_events(run.run_id)
                )
            )
            graph = graph_service.build_graph("reproduce", service.list_events(run.run_id))
            self.assertEqual(graph[-1]["id"], "outputs")
            self.assertEqual(graph[-1]["status"], "success")

    def test_command_action_execute_edit_reject_and_idempotency(self) -> None:
        service = InMemoryRunService()
        run = service.create_run(
            RunCreateRequest(
                mode="reproduce",
                project_id="project_agents",
                task="Run generated smoke check",
                pdf_path=__file__,
                mock_mode=True,
                run_pipeline=False,
            )
        )
        action = service._command_action_from_result(
            run.run_id,
            {
                "implementation_bundle": {
                    "smoke_test_command": "python --version",
                },
            },
            RunCreateRequest(mode="reproduce", pdf_path=__file__),
        )
        self.assertIsNotNone(action)
        service._actions[run.run_id] = [action]

        edited = service.edit_action(
            action.action_id,
            ActionEditRequest(
                edited_command="python --version",
                reason="Use a bounded version check",
            ),
        )
        self.assertIsNotNone(edited)
        self.assertEqual(edited.status, "edited")
        self.assertEqual(edited.execution_status, "not_started")

        executed = service.execute_action(action.action_id)
        self.assertIsNotNone(executed)
        self.assertEqual(executed.execution_status, "succeeded")
        self.assertIsNotNone(executed.command_result)
        self.assertTrue(executed.command_result.executed)

        duplicate = service.execute_action(action.action_id)
        self.assertIsNotNone(duplicate)
        self.assertEqual(duplicate.execution_status, "succeeded")
        success_events = [
            event for event in service.list_events(run.run_id)
            if event.event_type == "action_execution_succeeded"
        ]
        self.assertEqual(len(success_events), 1)

        approved_run = service.create_run(
            RunCreateRequest(mode="reproduce", pdf_path=__file__)
        )
        approved_action = service._command_action_from_result(
            approved_run.run_id,
            {
                "implementation_bundle": {
                    "smoke_test_command": "python --version",
                },
            },
            RunCreateRequest(mode="reproduce", pdf_path=__file__),
        )
        self.assertIsNotNone(approved_action)
        service._actions[approved_run.run_id] = [approved_action]
        approved = service.approve_action(approved_action.action_id)
        self.assertEqual(approved.status, "approved")
        executed_after_approval = service.execute_action(approved_action.action_id)
        self.assertIsNotNone(executed_after_approval)
        self.assertEqual(executed_after_approval.execution_status, "succeeded")

        rejected_run = service.create_run(
            RunCreateRequest(mode="reproduce", pdf_path=__file__)
        )
        reject_action = service._command_action_from_result(
            rejected_run.run_id,
            {
                "implementation_bundle": {
                    "smoke_test_command": "python --version",
                },
            },
            RunCreateRequest(mode="reproduce", pdf_path=__file__),
        )
        self.assertIsNotNone(reject_action)
        service._actions[rejected_run.run_id] = [reject_action]
        rejected = service.reject_action(reject_action.action_id)
        self.assertEqual(rejected.status, "rejected")
        with self.assertRaises(ValueError):
            service.execute_action(reject_action.action_id)

    def test_blocked_command_action_records_non_executed_result(self) -> None:
        service = InMemoryRunService()
        run = service.create_run(
            RunCreateRequest(mode="reproduce", pdf_path=__file__)
        )
        action = service._command_action_from_result(
            run.run_id,
            {"command_plans": [{"command": "rm -rf .", "purpose": "unsafe"}]},
            RunCreateRequest(mode="reproduce", pdf_path=__file__),
        )
        self.assertIsNotNone(action)
        service._actions[run.run_id] = [action]

        executed = service.execute_action(action.action_id)
        self.assertIsNotNone(executed)
        self.assertEqual(executed.execution_status, "blocked")
        self.assertIsNotNone(executed.command_result)
        self.assertFalse(executed.command_result.executed)
        self.assertIsNotNone(executed.blocked_reason)

    def test_failed_command_action_is_distinct_from_policy_block(self) -> None:
        service = InMemoryRunService()
        run = service.create_run(
            RunCreateRequest(mode="reproduce", pdf_path=__file__)
        )
        action = service._command_action_from_result(
            run.run_id,
            {
                "implementation_bundle": {
                    "smoke_test_command": "python demo.py --help",
                },
            },
            RunCreateRequest(mode="reproduce", pdf_path=__file__),
        )
        self.assertIsNotNone(action)
        service._actions[run.run_id] = [action]

        executed = service.execute_action(action.action_id)
        self.assertIsNotNone(executed)
        self.assertEqual(executed.execution_status, "failed")
        self.assertIsNotNone(executed.command_result)
        self.assertTrue(executed.command_result.executed)
        self.assertIsNone(executed.blocked_reason)

    def test_patch_action_execution_applies_known_patch_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            target = workspace / "main.py"
            target.write_text("print('old')\n", encoding="utf-8")

            patches = PatchService(project_root=root, patch_roots=[workspace])
            proposal = patches.propose_patch(
                "run_patch",
                PatchProposeRequest(
                    path="workspace/main.py",
                    new_content="print('new')\n",
                    reason="test patch",
                ),
            )
            service = InMemoryRunService()
            run = service.create_run(
                RunCreateRequest(mode="reproduce", pdf_path=__file__)
            )

            with patch("backend.services.run_service.patch_service", patches):
                actions = service._patch_actions_from_result(
                    run.run_id,
                    {"patch_id": proposal.patch_id, "reason": "apply test patch"},
                )
                self.assertEqual(len(actions), 1)
                service._actions[run.run_id] = actions
                executed = service.execute_action(actions[0].action_id)

            self.assertIsNotNone(executed)
            self.assertEqual(executed.execution_status, "succeeded")
            self.assertEqual(target.read_text(encoding="utf-8"), "print('new')\n")
            self.assertIsNotNone(executed.patch_result)
            self.assertTrue(executed.patch_result.syntax_ok)
            event_types = [event.event_type for event in service.list_events(run.run_id)]
            self.assertIn("patch_applied", event_types)
            self.assertIn("syntax_check_passed", event_types)

    def test_patch_service_reports_structured_syntax_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            target = workspace / "broken.py"
            target.write_text("print('old')\n", encoding="utf-8")

            service = PatchService(project_root=root, patch_roots=[workspace])
            proposal = service.propose_patch(
                "run_patch",
                PatchProposeRequest(
                    path="workspace/broken.py",
                    new_content="def broken(:\n",
                    reason="test syntax failure",
                ),
            )

            result = service.apply_patch(proposal.patch_id)

            self.assertIsNotNone(result)
            self.assertTrue(result.applied)
            self.assertFalse(result.syntax_ok)
            self.assertEqual(result.syntax_failures[0]["path"], "workspace/broken.py")
            self.assertIn("Syntax", result.syntax_failures[0]["error"])
            self.assertEqual(target.read_text(encoding="utf-8"), "def broken(:\n")

    def test_patch_apply_route_requests_action_without_writing_file(self) -> None:
        from backend.routers import patches as patch_router

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            target = workspace / "main.py"
            target.write_text("print('old')\n", encoding="utf-8")

            patch_store = PatchService(project_root=root, patch_roots=[workspace])
            proposal = patch_store.propose_patch(
                "run_patch",
                PatchProposeRequest(
                    path="workspace/main.py",
                    new_content="print('new')\n",
                    reason="test request action",
                ),
            )
            created_actions: list[ActionRequest] = []

            def create_patch_action(run_id: str, patch_id: str) -> ActionRequest:
                action = ActionRequest(
                    action_id="act_patch",
                    run_id=run_id,
                    agent="Prototype Builder Agent",
                    tool="apply_patch",
                    patch_id=patch_id,
                    path=proposal.path,
                    risk="medium",
                    reason="Apply generated patch proposal.",
                )
                created_actions.append(action)
                return action

            with patch.object(patch_router, "patch_service", patch_store), patch.object(
                patch_router.run_service,
                "create_patch_action",
                side_effect=create_patch_action,
            ):
                action = patch_router.request_apply_patch("run_patch", proposal.patch_id)

            self.assertEqual(action.action_id, "act_patch")
            self.assertEqual(action.patch_id, proposal.patch_id)
            self.assertEqual(len(created_actions), 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "print('old')\n")

    def test_websocket_stream_pushes_events_emitted_after_connect(self) -> None:
        from backend.main import run_event_stream
        from backend.services.event_service import event_service

        async def scenario() -> None:
            run_id = "run_ws_live_test"
            websocket = FakeWebSocket()
            with patch("backend.main.event_service.list_events", return_value=[]):
                task = asyncio.create_task(run_event_stream(websocket, run_id))
                for _ in range(50):
                    if event_service._subscribers.get(run_id):
                        break
                    await asyncio.sleep(0.01)
                event_service.emit(
                    WorkbenchEvent(
                        event_id="evt_live",
                        run_id=run_id,
                        node="planner",
                        agent="Planning Agent",
                        event_type="node_started",
                        status="running",
                        message="Live event",
                        created_at="2026-01-01T00:00:00Z",
                    )
                )
                for _ in range(50):
                    if websocket.sent:
                        break
                    await asyncio.sleep(0.01)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task

            self.assertEqual(websocket.sent[0]["event_id"], "evt_live")
            self.assertEqual(websocket.sent[0]["event_type"], "node_started")

        asyncio.run(scenario())

    def test_productize_revision_request_records_event_and_history(self) -> None:
        service = InMemoryRunService()
        run = service.create_run(
            RunCreateRequest(
                mode="productize",
                pdf_path=__file__,
                product_goal="Improve evaluator feedback",
            )
        )
        service._store_result(
            run.run_id,
            {
                "pipeline_status": "complete",
                "revision_history": [],
            },
        )

        result = service.request_revision(
            run.run_id,
            issue_id="eval-suggestion-1",
            action="revise_prd",
            instruction="Clarify MVP scope",
        )

        self.assertEqual(result.run_id, run.run_id)
        self.assertEqual(result.action, "revise_prd")
        stored = service.get_result(run.run_id)
        self.assertEqual(stored["revision_history"][0]["issue_id"], "eval-suggestion-1")
        event_types = [event.event_type for event in service.list_events(run.run_id)]
        self.assertIn("revision_requested", event_types)

    def test_progress_stage_maps_to_structured_graph_node(self) -> None:
        self.assertEqual(
            InMemoryRunService._graph_node_for_progress_stage(
                "Product Planner Agent generated PRD and MVP scope.",
                "productize",
            ),
            "prd",
        )
        self.assertEqual(
            InMemoryRunService._graph_node_for_progress_stage(
                "Reproduction Planner Agent generated command plan.",
                "reproduce",
            ),
            "planning",
        )
        self.assertEqual(
            InMemoryRunService._graph_node_for_progress_stage(
                "Product Evaluator Agent scoring prototype",
                "productize",
            ),
            "evaluation",
        )
        self.assertEqual(
            InMemoryRunService._graph_node_for_progress_stage(
                "Inspecting generated product",
                "productize",
            ),
            "scaffold",
        )

    def test_productize_proposal_review_graph_stops_before_execution_nodes(self) -> None:
        events = [
            WorkbenchEvent(
                event_id="evt_intake",
                run_id="run_productize_graph",
                node="run_intake",
                agent="Workbench",
                event_type="run_created",
                status="success",
                message="Created productize run.",
                created_at="2026-01-01T00:00:00Z",
            ),
            WorkbenchEvent(
                event_id="evt_parse",
                run_id="run_productize_graph",
                node="parse",
                agent="PaperPilot Agent",
                event_type="node_started",
                status="running",
                message="Generating Productize proposals for review",
                created_at="2026-01-01T00:00:01Z",
            ),
            WorkbenchEvent(
                event_id="evt_prd",
                run_id="run_productize_graph",
                node="prd",
                agent="PaperPilot Agent",
                event_type="node_started",
                status="running",
                message="Product Planner Agent building PRD and MVP",
                created_at="2026-01-01T00:00:02Z",
            ),
            WorkbenchEvent(
                event_id="evt_review",
                run_id="run_productize_graph",
                node="agent_runtime",
                agent="Workbench Runner",
                event_type="pipeline_finished",
                status="waiting_review",
                message="productize agent pipeline completed with review items.",
                payload={"pipeline_status": "proposal_review"},
                created_at="2026-01-01T00:00:03Z",
            ),
        ]

        graph = graph_service.build_graph("productize", events)
        labels = {node["id"]: node["label"] for node in graph}
        statuses = {node["id"]: node["status"] for node in graph}

        self.assertEqual(labels["mvp"], "Proposal Review")
        self.assertEqual(statuses["prd"], "success")
        self.assertEqual(statuses["mvp"], "waiting_review")
        self.assertEqual(statuses["prototype"], "pending")
        self.assertEqual(statuses["evaluation"], "pending")
        self.assertEqual(statuses["revision"], "pending")
        self.assertEqual(statuses["scaffold"], "pending")

    def test_productize_executed_proposal_graph_reaches_scaffold(self) -> None:
        events = [
            WorkbenchEvent(
                event_id="evt_parse",
                run_id="run_productize_executed_graph",
                node="parse",
                agent="PaperPilot Agent",
                event_type="node_started",
                status="running",
                message="Generating Productize proposals for review",
                created_at="2026-01-01T00:00:01Z",
            ),
            WorkbenchEvent(
                event_id="evt_review",
                run_id="run_productize_executed_graph",
                node="agent_runtime",
                agent="Workbench Runner",
                event_type="pipeline_finished",
                status="waiting_review",
                message="productize agent pipeline completed with review items.",
                payload={"pipeline_status": "proposal_review"},
                created_at="2026-01-01T00:00:02Z",
            ),
            WorkbenchEvent(
                event_id="evt_prototype",
                run_id="run_productize_executed_graph",
                node="prototype",
                agent="PaperPilot Agent",
                event_type="node_started",
                status="running",
                message="Prototype Builder Agent planning interface and adapter",
                created_at="2026-01-01T00:00:03Z",
            ),
            WorkbenchEvent(
                event_id="evt_eval",
                run_id="run_productize_executed_graph",
                node="evaluation",
                agent="PaperPilot Agent",
                event_type="node_started",
                status="running",
                message="Product Evaluator Agent scoring prototype",
                created_at="2026-01-01T00:00:04Z",
            ),
            WorkbenchEvent(
                event_id="evt_executed",
                run_id="run_productize_executed_graph",
                node="agent_runtime",
                agent="Workbench Runner",
                event_type="proposal_executed",
                status="success",
                message="Executed product proposal: Demo.",
                payload={"pipeline_status": "complete"},
                created_at="2026-01-01T00:00:05Z",
            ),
        ]

        graph = graph_service.build_graph("productize", events)
        statuses = {node["id"]: node["status"] for node in graph}

        self.assertEqual(statuses["prototype"], "success")
        self.assertEqual(statuses["evaluation"], "success")
        self.assertEqual(statuses["scaffold"], "success")

    def test_productize_proposal_failure_stays_on_latest_started_stage(self) -> None:
        events = [
            WorkbenchEvent(
                event_id="evt_parse",
                run_id="run_productize_failed_graph",
                node="parse",
                agent="PaperPilot Agent",
                event_type="node_started",
                status="running",
                message="Generating Productize proposals for review",
                created_at="2026-01-01T00:00:01Z",
            ),
            WorkbenchEvent(
                event_id="evt_capability",
                run_id="run_productize_failed_graph",
                node="parse",
                agent="PaperPilot Agent",
                event_type="node_started",
                status="running",
                message="Research Synthesizer Agent extracting capability for Paper",
                created_at="2026-01-01T00:00:02Z",
            ),
            WorkbenchEvent(
                event_id="evt_failed",
                run_id="run_productize_failed_graph",
                node="agent_runtime",
                agent="Workbench Runner",
                event_type="pipeline_failed",
                status="failed",
                message="Agent pipeline failed: cannot schedule new futures after interpreter shutdown",
                payload={"pipeline_status": "failed"},
                created_at="2026-01-01T00:00:03Z",
            ),
        ]

        graph = graph_service.build_graph("productize", events)
        statuses = {node["id"]: node["status"] for node in graph}

        self.assertEqual(statuses["capability_cards"], "failed")
        self.assertEqual(statuses["scaffold"], "pending")

    def test_productize_failed_proposal_marks_error_agent_node(self) -> None:
        events = [
            WorkbenchEvent(
                event_id="evt_review",
                run_id="run_productize_failed_execute",
                node="agent_runtime",
                agent="Workbench Runner",
                event_type="pipeline_finished",
                status="waiting_review",
                message="Product proposals are ready; choose one to scaffold.",
                payload={"pipeline_status": "proposal_review"},
                created_at="2026-01-01T00:00:01Z",
            ),
            WorkbenchEvent(
                event_id="evt_eval",
                run_id="run_productize_failed_execute",
                node="evaluation",
                agent="PaperPilot Agent",
                event_type="node_started",
                status="running",
                message="Product Evaluator Agent scoring prototype",
                created_at="2026-01-01T00:00:02Z",
            ),
            WorkbenchEvent(
                event_id="evt_executed_failed",
                run_id="run_productize_failed_execute",
                node="agent_runtime",
                agent="Workbench Runner",
                event_type="proposal_executed",
                status="failed",
                message="Executed product proposal: Demo.",
                payload={
                    "pipeline_status": "failed",
                    "errors": ["[Prototype Builder Agent] No LLM API key is configured."],
                },
                created_at="2026-01-01T00:00:03Z",
            ),
        ]

        graph = graph_service.build_graph("productize", events)
        statuses = {node["id"]: node["status"] for node in graph}

        self.assertEqual(statuses["prototype"], "failed")
        self.assertEqual(statuses["evaluation"], "pending")
        self.assertEqual(statuses["scaffold"], "pending")

    def test_artifact_and_file_services_are_read_only_and_root_limited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "outputs"
            workspace = root / "workspace"
            outputs.mkdir()
            workspace.mkdir()
            (outputs / "other").mkdir()
            (outputs / "report.md").write_text("# Report\n", encoding="utf-8")
            (outputs / "other" / "report.md").write_text(
                "# Other\n",
                encoding="utf-8",
            )
            (workspace / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (workspace / "sandboxes").mkdir()
            (workspace / "sandboxes" / "scratch.py").write_text(
                "print('skip')\n",
                encoding="utf-8",
            )

            artifacts = ArtifactService(
                project_root=root,
                artifact_roots=[outputs],
            )
            listed_artifacts = artifacts.list_artifacts(run_id="run_test")
            self.assertIn(
                "outputs/report.md",
                {item.path for item in listed_artifacts},
            )
            filtered_artifacts = artifacts.list_artifacts(
                run_id="run_test",
                prefixes=["outputs/other"],
            )
            self.assertEqual(
                [item.path for item in filtered_artifacts],
                ["outputs/other/report.md"],
            )
            report = artifacts.read_artifact("outputs/report.md")
            self.assertIn("# Report", report.content)

            files = FileService(project_root=root, file_roots=[workspace])
            listed_files = files.list_files()
            self.assertEqual(listed_files[0].path, "workspace/main.py")
            self.assertNotIn(
                "workspace/sandboxes/scratch.py",
                {item.path for item in listed_files},
            )
            content = files.read_content("workspace/main.py")
            self.assertIn("ok", content.content)

            with self.assertRaises(PermissionError):
                files.read_content("outputs/report.md")

    def test_file_service_scopes_files_to_current_run_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            outputs = root / "outputs"
            current = workspace / "generated_reproduction_current"
            old = workspace / "generated_reproduction_old"
            code_output = outputs / "paper" / "code"
            current.mkdir(parents=True)
            old.mkdir(parents=True)
            code_output.mkdir(parents=True)
            (current / "main.py").write_text("print('current')\n", encoding="utf-8")
            (current / "README.md").write_text("# Current\n", encoding="utf-8")
            (old / "main.py").write_text("print('old')\n", encoding="utf-8")
            (code_output / "report.md").write_text("# Code report\n", encoding="utf-8")

            files = FileService(
                project_root=root,
                file_roots=[workspace, outputs],
                run_root_resolver=lambda run_id: [current, code_output]
                if run_id == "run_current"
                else [],
            )

            listed = files.list_files("run_current")
            listed_paths = {item.path for item in listed}
            self.assertIn("workspace/generated_reproduction_current/main.py", listed_paths)
            self.assertIn("outputs/paper/code/report.md", listed_paths)
            self.assertNotIn("workspace/generated_reproduction_old/main.py", listed_paths)
            content = files.read_content(
                "workspace/generated_reproduction_current/main.py",
                run_id="run_current",
            )
            self.assertIn("current", content.content)

            with self.assertRaises(PermissionError):
                files.read_content(
                    "workspace/generated_reproduction_old/main.py",
                    run_id="run_current",
                )

    def test_patch_service_only_updates_generated_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            target = workspace / "main.py"
            target.write_text("print('old')\n", encoding="utf-8")

            service = PatchService(project_root=root, patch_roots=[workspace])
            patch = service.propose_patch(
                "run_test",
                request=PatchProposeRequest(
                    path="workspace/main.py",
                    new_content="print('new')\n",
                    reason="test patch",
                ),
            )

            self.assertIn("-print('old')", patch.unified_diff)
            result = service.apply_patch(patch.patch_id)
            self.assertIsNotNone(result)
            self.assertTrue(result.applied)
            self.assertEqual(target.read_text(encoding="utf-8"), "print('new')\n")

            with self.assertRaises(PermissionError):
                service.propose_patch(
                    "run_test",
                    request=PatchProposeRequest(
                        path="outside.py",
                        new_content="",
                    ),
                )

    def test_check_and_command_services_use_existing_safety_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "main.py").write_text("print('ok')\n", encoding="utf-8")

            checks = CheckService(project_root=root, check_roots=[workspace])
            syntax = checks.syntax_check(
                SyntaxCheckRequest(path="workspace/main.py")
            )
            self.assertTrue(syntax.success)

            commands = CommandService(project_root=root)
            review = commands.review_command(
                "run_test",
                CommandReviewRequest(command="python --version", cwd="."),
            )
            self.assertEqual(review.risk_level, "low")
            blocked = commands.review_command(
                "run_test",
                CommandReviewRequest(command="rm -rf .", cwd="."),
            )
            self.assertEqual(blocked.risk_level, "blocked")


if __name__ == "__main__":
    unittest.main()
