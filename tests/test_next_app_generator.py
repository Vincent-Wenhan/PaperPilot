"""Tests for the Next.js app generator and bundle writer."""
from __future__ import annotations

from pathlib import Path

import pytest

from productize import generate_nextjs_app
from productize.next_app_generator import build_bundle, build_contract
from productize.next_app_writer import (
    MAX_FILES,
    MAX_TOTAL_BYTES,
    validate_generated_path,
    write_bundle,
)
from schemas.generated_app import (
    AppContract,
    GeneratedAppBundle,
    GeneratedFile,
)
from schemas.product_schema import (
    PRD,
    ProductOpportunity,
    ProductPlan,
    ValueProposition,
)


@pytest.fixture
def sample_plan() -> ProductPlan:
    return ProductPlan(
        jtbd="Help researchers explore papers interactively",
        value_proposition=ValueProposition(),
        selected_product="PaperPilot Demo",
        selection_reason="Best fit for demo",
        prd=PRD(
            product_name="PaperPilot Demo",
            problem_statement="Make paper reproduction accessible",
            target_users=["Researchers"],
            goals=["Demonstrate paper capability"],
            non_goals=["Production deployment"],
            core_features=["Upload paper", "Run mock prediction"],
            user_flow=["Upload", "Predict", "Review"],
            success_metrics=["E2E tests pass"],
            risks=["Mock might not match real model"],
            limitations=["No real model integration"],
        ),
        opportunities=[
            ProductOpportunity(
                idea_name="Demo",
                target_user="Researchers",
                core_value="Make paper accessible",
                technical_feasibility=4,
                demo_feasibility=4,
                model_availability=4,
                data_requirement=2,
                integration_risk=3,
                user_value=4,
                course_presentation_value=4,
                overall_score=4.0,
                reason="Good fit for demo",
            )
        ],
        risks=["Mock might not match real model"],
        limitations=["No real model integration"],
    )


def test_validate_generated_path_accepts_app_routes() -> None:
    path = validate_generated_path("app/api/predict/route.ts")
    assert path.as_posix() == "app/api/predict/route.ts"


def test_validate_generated_path_accepts_root_files() -> None:
    path = validate_generated_path("package.json")
    assert path.as_posix() == "package.json"


def test_validate_generated_path_rejects_absolute() -> None:
    with pytest.raises(ValueError, match="Unsafe generated path"):
        validate_generated_path("/etc/passwd")


def test_validate_generated_path_rejects_parent_traversal() -> None:
    with pytest.raises(ValueError, match="Unsafe generated path"):
        validate_generated_path("../package.json")


def test_validate_generated_path_rejects_unknown_root() -> None:
    with pytest.raises(ValueError, match="Unexpected root directory"):
        validate_generated_path("evil/hack.ts")


def test_build_contract_has_required_scripts(sample_plan: ProductPlan) -> None:
    contract = build_contract(sample_plan)
    assert contract.runtime == "nextjs"
    assert contract.package_manager == "npm"
    assert contract.required_scripts["dev"] == "next dev"
    assert contract.required_scripts["build"] == "next build"
    assert contract.required_scripts["start"] == "next start"
    assert contract.required_scripts["test"] == "vitest run"
    assert contract.real_adapter_required is True
    assert contract.mock_fallback_allowed is True


def test_build_bundle_includes_core_files(sample_plan: ProductPlan) -> None:
    bundle = build_bundle(sample_plan, repo_path="repo")
    paths = {f.path for f in bundle.files}
    assert "package.json" in paths
    assert "tsconfig.json" in paths
    assert "next.config.mjs" in paths
    assert "app/layout.tsx" in paths
    assert "app/page.tsx" in paths
    assert "app/api/health/route.ts" in paths
    assert "app/api/predict/route.ts" in paths
    assert "lib/adapter.ts" in paths
    assert "tests/e2e/product.spec.ts" in paths
    assert "README.md" in paths
    assert len(bundle.files) <= MAX_FILES
    total = sum(len(f.content.encode("utf-8")) for f in bundle.files)
    assert total <= MAX_TOTAL_BYTES


def test_build_bundle_adapter_has_mock_first_default(
    sample_plan: ProductPlan,
) -> None:
    bundle = build_bundle(sample_plan, repo_path="repo")
    adapter = next(f for f in bundle.files if f.path == "lib/adapter.ts")
    assert "PAPERPILOT_MOCK_MODE" in adapter.content
    assert "runPrediction" in adapter.content
    assert "mock" in adapter.content


def test_write_bundle_creates_files(tmp_path: Path, sample_plan: ProductPlan) -> None:
    destination = tmp_path / "gen"
    bundle = build_bundle(sample_plan, repo_path="repo")
    manifest = write_bundle(bundle, destination)
    assert destination.is_dir()
    assert (destination / "package.json").is_file()
    assert (destination / "app" / "api" / "predict" / "route.ts").is_file()
    assert len(manifest["files"]) == len(bundle.files)
    assert manifest["contract"]["runtime"] == "nextjs"


def test_write_bundle_rejects_too_many_files(tmp_path: Path) -> None:
    files = [
        GeneratedFile(path=f"app/file_{i}.ts", content="x", purpose="test")
        for i in range(MAX_FILES + 1)
    ]
    bundle = GeneratedAppBundle(
        contract=AppContract(required_routes=[], required_components=[], required_api_routes=[], acceptance_tests=[]),
        files=files,
    )
    with pytest.raises(ValueError, match="Too many generated files"):
        write_bundle(bundle, tmp_path / "gen")


def test_write_bundle_rejects_duplicate_paths(tmp_path: Path) -> None:
    files = [
        GeneratedFile(path="app/page.tsx", content="x", purpose="test"),
        GeneratedFile(path="app/page.tsx", content="y", purpose="dup"),
    ]
    bundle = GeneratedAppBundle(
        contract=AppContract(required_routes=[], required_components=[], required_api_routes=[], acceptance_tests=[]),
        files=files,
    )
    with pytest.raises(ValueError, match="Duplicate file"):
        write_bundle(bundle, tmp_path / "gen")


def test_write_bundle_rejects_unsafe_path(tmp_path: Path) -> None:
    files = [
        GeneratedFile(path="../escape.ts", content="x", purpose="hack"),
    ]
    bundle = GeneratedAppBundle(
        contract=AppContract(required_routes=[], required_components=[], required_api_routes=[], acceptance_tests=[]),
        files=files,
    )
    with pytest.raises(ValueError):
        write_bundle(bundle, tmp_path / "gen")


def test_generate_nextjs_app_returns_manifest(
    tmp_path: Path, sample_plan: ProductPlan
) -> None:
    destination = tmp_path / "gen"
    result = generate_nextjs_app(sample_plan, destination, repo_path="repo")
    assert result["contract"]["runtime"] == "nextjs"
    assert result["contract"]["package_manager"] == "npm"
    assert len(result["files"]) > 10
    assert any(f["path"] == "package.json" for f in result["files"])
