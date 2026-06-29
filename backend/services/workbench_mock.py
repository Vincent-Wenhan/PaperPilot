"""Mock workbench data used by the API facade before live runs are attached."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.schemas import (
    ActionRequest,
    ArtifactSummary,
    FileNode,
    RunRecord,
    WorkbenchEvent,
    WorkbenchSnapshot,
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def build_mock_run(run_id: str = "run_mock_reproduce") -> RunRecord:
    now = utc_now()
    return RunRecord(
        run_id=run_id,
        project_id="project_demo",
        mode="reproduce",
        status="waiting_review",
        task="Reproduce a paper with repository evidence and bounded runner checks.",
        created_at=now,
        updated_at=now,
        summary="[MOCK] Reproduce workflow paused at runner review. This is a seeded mock run, not real pipeline state.",
        plan=[
            "Parse paper and extract resource links",
            "Build structured research understanding",
            "Scan repository entrypoints and dependencies",
            "Generate reproduction plan",
            "Review medium-risk smoke-test command",
            "Diagnose execution result and write report",
        ],
    )


def build_mock_events(run_id: str) -> list[WorkbenchEvent]:
    now = utc_now()
    return [
        WorkbenchEvent(
            event_id="evt_mock_seed",
            run_id=run_id,
            node="run_intake",
            agent="Workbench",
            event_type="run_created",
            status="success",
            message="[MOCK] Seeded a mock run for workbench preview. Start a real run to see pipeline state.",
            payload={"mock": True},
            created_at=now,
        ),
        WorkbenchEvent(
            event_id="evt_parse_finished",
            run_id=run_id,
            node="parse_paper",
            agent="PDF Parser",
            event_type="node_finished",
            status="success",
            message="Paper text and resource links extracted.",
            payload={"pages": 14, "mock": True},
            created_at=now,
        ),
        WorkbenchEvent(
            event_id="evt_repo_tool_call",
            run_id=run_id,
            node="repository_understanding",
            agent="Repository Understanding Agent",
            event_type="tool_call",
            status="success",
            message="code_search found train.py, eval.py, and config/default.yaml.",
            payload={"tool": "code_search", "query": "argparse", "mock": True},
            created_at=now,
        ),
        WorkbenchEvent(
            event_id="evt_review_required",
            run_id=run_id,
            node="runner_review",
            agent="Reproduction Planner Agent",
            event_type="human_review_required",
            status="waiting_review",
            message="Command classified as review-required.",
            payload={"command": "python main.py --smoke-test", "risk": "medium", "mock": True},
            created_at=now,
        ),
    ]


def build_mock_actions(run_id: str) -> list[ActionRequest]:
    return [
        ActionRequest(
            action_id="act_smoke_test",
            run_id=run_id,
            agent="Reproduction Planner Agent",
            tool="run_command",
            command="python main.py --smoke-test",
            risk="medium",
            reason="[MOCK] Validate generated entrypoint with synthetic inputs only.",
        )
    ]


def build_mock_artifacts(run_id: str) -> list[ArtifactSummary]:
    return [
        ArtifactSummary(
            artifact_id="examples/sample_outputs/reproduction_plan.md",
            run_id=run_id,
            name="reproduction_plan.md",
            kind="plan",
            path="examples/sample_outputs/reproduction_plan.md",
            size_bytes=0,
        ),
        ArtifactSummary(
            artifact_id="examples/sample_outputs/run.sh",
            run_id=run_id,
            name="run.sh",
            kind="runner",
            path="examples/sample_outputs/run.sh",
            size_bytes=0,
            status="waiting_review",
        ),
        ArtifactSummary(
            artifact_id="examples/sample_outputs/report.md",
            run_id=run_id,
            name="report.md",
            kind="report",
            path="examples/sample_outputs/report.md",
            size_bytes=0,
            status="pending",
        ),
    ]


def build_mock_files() -> list[FileNode]:
    return [
        FileNode(
            path="workspace/generated_code/main.py",
            name="main.py",
            kind="file",
            size_bytes=0,
        ),
        FileNode(
            path="generated_product/example/index.html",
            name="index.html",
            kind="file",
            size_bytes=0,
        ),
    ]


def build_workbench_snapshot() -> WorkbenchSnapshot:
    run = build_mock_run()
    return WorkbenchSnapshot(
        project_id=run.project_id,
        active_run=run,
        events=build_mock_events(run.run_id),
        actions=build_mock_actions(run.run_id),
        artifacts=build_mock_artifacts(run.run_id),
        files=build_mock_files(),
    )
