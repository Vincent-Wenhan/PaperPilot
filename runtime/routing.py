"""Deterministic routing helpers for PaperPilot graphs."""

from __future__ import annotations

from typing import Any


def route_after_evaluation(state: dict[str, Any]) -> str:
    """Route Productize revisions from score and evaluator suggestions."""
    evaluation = state.get("evaluation") or {}
    score = float(evaluation.get("overall_score") or 0)
    revision_count = int(state.get("revision_count") or 0)
    max_revisions = int(state.get("max_revisions") or 1)
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
