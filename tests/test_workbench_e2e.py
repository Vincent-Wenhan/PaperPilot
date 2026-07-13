"""End-to-end tests for the workbench backend.

These tests verify the cancel/retry/resume endpoints added in the
deep-modification plan.  They run against the in-memory FastAPI app via
``TestClient``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from backend.errors import WorkbenchError
from backend.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cancel_run_returns_cancelled_status() -> None:
    run_payload = {
        "mode": "reproduce",
        "project_id": "test-cancel",
        "task": "test cancel",
        "pdf_path": "test.pdf",
        "run_pipeline": False,
    }
    create_response = client.post("/api/runs", json=run_payload)
    assert create_response.status_code == 200
    run_id = create_response.json()["run_id"]

    cancel_response = client.post(
        f"/api/runs/{run_id}/cancel",
        json={"reason": "user changed mind"},
    )
    assert cancel_response.status_code == 200
    body = cancel_response.json()
    assert body["status"] == "cancelled"
    assert "user changed mind" in body["summary"]


def test_cancel_nonexistent_run_returns_404() -> None:
    response = client.post(
        "/api/runs/nonexistent-run/cancel",
        json={"reason": "test"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"


def test_resume_run_transitions_to_running() -> None:
    run_payload = {
        "mode": "reproduce",
        "project_id": "test-resume",
        "task": "test resume",
        "pdf_path": "test.pdf",
        "run_pipeline": False,
    }
    create_response = client.post("/api/runs", json=run_payload)
    run_id = create_response.json()["run_id"]

    resume_response = client.post(
        f"/api/runs/{run_id}/resume",
        json={"approved": True, "feedback": "looks good"},
    )
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "running"


def test_retry_failed_run_restarts_pipeline() -> None:
    run_payload = {
        "mode": "reproduce",
        "project_id": "test-retry",
        "task": "test retry",
        "pdf_path": "test.pdf",
        "run_pipeline": False,
    }
    create_response = client.post("/api/runs", json=run_payload)
    run_id = create_response.json()["run_id"]

    # Mark as failed via cancel since retry requires failed/cancelled state
    cancel_response = client.post(
        f"/api/runs/{run_id}/cancel",
        json={"reason": "test"},
    )
    assert cancel_response.status_code == 200

    retry_response = client.post(
        f"/api/runs/{run_id}/retry",
        json={"from_step": "start"},
    )
    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "running"


def test_structured_error_envelope() -> None:
    """InvalidArgument errors should return {error: {code, message}}."""

    response = client.post(
        "/api/runs/nonexistent-run/resume",
        json={"approved": True, "feedback": ""},
    )
    # Resume on nonexistent run returns 404
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "not_found"


if __name__ == "__main__":
    test_health_endpoint()
    test_cancel_run_returns_cancelled_status()
    test_cancel_nonexistent_run_returns_404()
    test_resume_run_transitions_to_running()
    test_retry_failed_run_restarts_pipeline()
    test_structured_error_envelope()
    print("All workbench e2e tests passed.")
