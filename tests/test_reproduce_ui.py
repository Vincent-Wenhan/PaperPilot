from __future__ import annotations

from ui.shared import summarize_generated_project


def test_summarize_generated_project_includes_blueprint_quality() -> None:
    result = {
        "generated_repo_path": "/tmp/generated",
        "implementation_model": "gpt-4.1",
        "generated_files": ["main.py", "model.py", "tests/test_dataflow.py"],
        "implementation_blueprint": {"files": [{"path": "main.py"}, {"path": "model.py"}]},
        "code_quality": {"overall_score": 4.2, "passes_minimum_quality": True},
        "blueprint_quality": {"planned_files": 2, "missing_files": 0},
        "implementation_bundle": {"smoke_test_command": "python main.py --smoke-test"},
    }

    summary = summarize_generated_project(result)

    assert summary["status"] == "ready"
    assert summary["blueprint_file_count"] == 2
    assert summary["generated_file_count"] == 3
    assert summary["quality_score"] == 4.2
    assert summary["smoke_test_command"] == "python main.py --smoke-test"
