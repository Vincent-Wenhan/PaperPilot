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
            self.assertEqual(str(mocked_pipeline.call_args.args[0]), str(pdf))
            self.assertNotIn("secret-key", str(service.list_events(run.run_id)))
            self.assertEqual(
                service.get_result(run.run_id)["pipeline_status"],
                "complete",
            )

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
