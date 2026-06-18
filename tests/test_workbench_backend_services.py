from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.schemas import (
    ActionEditRequest,
    CommandReviewRequest,
    PatchProposeRequest,
    RunCreateRequest,
    SyntaxCheckRequest,
)
from backend.services.artifact_service import ArtifactService
from backend.services.check_service import CheckService
from backend.services.command_service import CommandService
from backend.services.file_service import FileService
from backend.services.patch_service import PatchService
from backend.services.run_service import InMemoryRunService
from backend.services.workbench_mock import build_workbench_snapshot


class WorkbenchBackendServiceTests(unittest.TestCase):
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
        action = service.list_actions(run.run_id)[0]

        approved = service.approve_action(action.action_id)
        self.assertIsNotNone(approved)
        self.assertEqual(approved.status, "approved")

        edited = service.edit_action(
            action.action_id,
            ActionEditRequest(
                edited_command="python main.py --help",
                reason="Use an even safer command",
            ),
        )
        self.assertIsNotNone(edited)
        self.assertEqual(edited.status, "edited")
        self.assertEqual(edited.edited_command, "python main.py --help")

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
            self.assertEqual(str(mocked_pipeline.call_args.args[0]), str(pdf))
            self.assertNotIn("secret-key", str(service.list_events(run.run_id)))
            self.assertEqual(
                service.get_result(run.run_id)["pipeline_status"],
                "complete",
            )

    def test_artifact_and_file_services_are_read_only_and_root_limited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outputs = root / "outputs"
            workspace = root / "workspace"
            outputs.mkdir()
            workspace.mkdir()
            (outputs / "report.md").write_text("# Report\n", encoding="utf-8")
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
            self.assertEqual(listed_artifacts[0].path, "outputs/report.md")
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
