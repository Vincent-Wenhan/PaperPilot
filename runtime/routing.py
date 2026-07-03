"""Deterministic routing helpers for PaperPilot graphs."""

from __future__ import annotations

from typing import Any

from schemas.runner_schema import AgentBudget


def _budget_from_state(state: dict[str, Any]) -> AgentBudget:
    raw = state.get("agent_budget") or {}
    if isinstance(raw, AgentBudget):
        return raw
    if isinstance(raw, dict):
        return AgentBudget.model_validate(raw)
    return AgentBudget()


def route_after_evaluation(state: dict[str, Any]) -> str:
    """Route Productize revisions from score and evaluator suggestions."""
    if state.get("product_verification"):
        return route_after_product_evaluation(state)

    evaluation = state.get("evaluation") or {}
    score = float(evaluation.get("overall_score") or 0)
    revision_count = int(state.get("revision_count") or 0)
    budget = _budget_from_state(state)
    max_revisions = int(state.get("max_revisions") or budget.max_revision_rounds)
    if score >= 4.0:
        return "finish"
    if revision_count >= max_revisions:
        return "finish_with_warnings"

    text = " ".join(
        [
            *evaluation.get("revision_suggestions", []),
            *evaluation.get("safety_warnings", []),
        ]
    ).lower()
    prototype_keywords = (
        "ui",
        "adapter",
        "mock",
        "syntax",
        "readme",
        "prototype",
    )
    if any(keyword in text for keyword in prototype_keywords):
        return "revise_prototype"
    return "revise_product_plan"


def route_after_product_evaluation(state: dict[str, Any]) -> str:
    """Route Productize revisions from blocking verification issues."""
    report = state.get("product_verification") or state.get("evaluation") or {}
    issues = report.get("issues") or []
    blocking = [
        issue
        for issue in issues
        if isinstance(issue, dict) and bool(issue.get("blocking"))
    ]
    score = float(report.get("score") or report.get("overall_score") or 0)
    revision_count = int(state.get("revision_count") or 0)
    budget = _budget_from_state(state)
    max_revisions = int(state.get("max_revisions") or budget.max_revision_rounds)

    if not blocking and (report.get("ok") is True or score >= 4.0):
        return "finish"
    if revision_count >= max_revisions:
        return "finish_with_warnings"

    routes = {
        str(issue.get("suggested_route") or "")
        for issue in blocking
    }
    if "revise_prototype" in routes:
        return "revise_prototype"
    if "reduce_mvp_scope" in routes or "revise_prd" in routes:
        return "revise_product_plan"
    return "revise_product_plan"


def route_command_plans(command_plans: list[dict[str, Any]]) -> str:
    """Return the highest-risk command route without executing commands."""
    levels = {
        str(plan.get("risk_level") or "medium").lower()
        for plan in command_plans
    }
    if "blocked" in levels:
        return "blocked"
    if levels.intersection({"medium", "high", "review", "sandbox"}):
        return "review"
    return "safe"


def route_after_code_review(state: dict[str, Any]) -> str:
    """Route Reproduce code revisions from code review score."""
    code_review = state.get("code_review") or {}
    verdict = str(code_review.get("verdict") or "revise")
    revision_count = int(state.get("code_revision_count") or 0)
    max_revisions = int(state.get("code_max_revisions") or 1)

    if verdict == "accept":
        return "accept"
    if revision_count >= max_revisions:
        return "finish_with_warnings"
    return "revise"


def route_after_second_review(state: dict[str, Any]) -> str:
    """Route after adversarial second review pass."""
    review = state.get("code_second_review") or {}
    verdict = str(review.get("verdict") or "revise")
    revision_count = int(state.get("code_revision_count") or 0)
    max_revisions = int(state.get("code_max_revisions") or 1)

    if verdict == "accept":
        return "accept"
    if revision_count >= max_revisions:
        return "finish_with_warnings"
    return "revise"


def route_after_sandbox_verify(state: dict[str, Any]) -> str:
    """Route to code_revise on smoke-test failure, otherwise to code_review/second_review."""
    sandbox = state.get("sandbox_verification") or {}
    smoke = state.get("smoke_test_result") or {}
    smoke_failed = bool(smoke) and not smoke.get("passed")
    sandbox_failed = bool(sandbox) and not sandbox.get("passed")

    if (smoke_failed or sandbox_failed) and not smoke.get("error") == "timeout":
        revision_count = int(state.get("code_revision_count") or 0)
        max_revisions = int(state.get("code_max_revisions") or 1)
        if revision_count < max_revisions:
            return "code_revise"

    if int(state.get("code_revision_count") or 0) > 0:
        return "second_review"
    return "code_review"


def route_after_verification(state: dict[str, Any]) -> str:
    """Route generated projects through verify -> repair -> verify."""
    report = state.get("verification_report") or state.get("sandbox_verification") or {}
    if report.get("ok") is True or report.get("passed") is True:
        if int(state.get("code_revision_count") or 0) > 0:
            return "second_review"
        return "code_review"

    repair_count = int(state.get("code_revision_count") or state.get("repair_count") or 0)
    budget = _budget_from_state(state)
    max_repairs = int(
        state.get("code_max_revisions")
        or state.get("max_repair_rounds")
        or budget.max_repair_rounds
    )
    if repair_count >= max_repairs:
        return "execution_diagnosis"
    return "code_repair"
