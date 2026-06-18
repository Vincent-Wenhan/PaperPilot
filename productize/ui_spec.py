"""Build structured UI specs for generated Productize prototypes."""

from __future__ import annotations

import re

from schemas.product_schema import (
    ProductPlan,
    ProductUISpec,
    PrototypePlan,
    ResultComponent,
    UIControl,
    UIStateCopy,
)


def _slug(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return cleaned[:48] or fallback


def _nonblank(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _unique_id(base_id: str, used_ids: set[str]) -> str:
    candidate = base_id
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base_id}_{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def _control_for_label(label: str, index: int, used_ids: set[str]) -> UIControl:
    lowered = label.lower()
    control_id = _unique_id(_slug(label, f"control_{index}"), used_ids)
    if any(word in lowered for word in ("threshold", "confidence", "sensitivity", "score")):
        return UIControl(
            control_id=control_id,
            label=label,
            control_type="slider",
            default=0.65,
            help_text="Tune the mock decision threshold.",
        )
    if any(word in lowered for word in ("mode", "type", "selector", "category", "module")):
        return UIControl(
            control_id=control_id,
            label=label,
            control_type="selectbox",
            default="Default",
            options=["Default", "Focused", "Broad"],
            help_text="Choose the mock workflow mode.",
        )
    if any(word in lowered for word in ("context", "notes", "scenario", "description")):
        return UIControl(
            control_id=control_id,
            label=label,
            control_type="textarea",
            default="",
            help_text="Provide optional context for the mock workflow.",
        )
    return UIControl(
        control_id=control_id,
        label=label,
        control_type="text_input",
        default="",
        help_text="Optional product-specific input.",
    )


def build_product_ui_spec(
    product_plan: ProductPlan,
    prototype_plan: PrototypePlan,
) -> ProductUISpec:
    """Normalize ProductPlan and PrototypePlan into renderable UI structure."""
    product_name = product_plan.prd.product_name or product_plan.selected_product or "Generated Product"
    page_sections = _nonblank(prototype_plan.page_structure) or [
        "Set up task",
        "Provide input",
        "Run mock analysis",
        "Review evidence and limitations",
        "Export result",
    ]
    input_labels = _nonblank(prototype_plan.user_inputs) or [
        f"{prototype_plan.template_type} input",
        "Decision context",
    ]
    used_control_ids: set[str] = set()
    controls = [
        _control_for_label(label, index, used_control_ids)
        for index, label in enumerate(input_labels[:6], 1)
    ]
    mock_schema = {
        str(key): str(type(value).__name__)
        for key, value in (prototype_plan.mock_result or {"summary": "mock result"}).items()
    }
    used_component_ids = {"mode"}
    result_components = [
        ResultComponent(
            component_id="mode",
            label="Mode",
            component_type="metric",
            source_key="type",
            description="Mock adapter output type.",
        )
    ]
    system_outputs = _nonblank(prototype_plan.system_outputs) or ["Structured mock result", "Downloadable JSON"]
    for index, output in enumerate(system_outputs, 1):
        result_components.append(
            ResultComponent(
                component_id=_unique_id(_slug(output, f"result_{index}"), used_component_ids),
                label=output,
                component_type="summary",
                source_key="result",
                description=output,
            )
        )
    return ProductUISpec(
        product_name=product_name,
        template_type=prototype_plan.template_type or "file",
        layout_mode="workflow_dashboard",
        page_sections=page_sections[:7],
        input_controls=controls,
        result_components=result_components[:8],
        mock_result_schema=mock_schema,
        states=UIStateCopy(
            empty=f"Provide input to start {product_name}.",
            loading="Running safe mock analysis.",
            success="Mock workflow completed.",
            error="Mock workflow failed before producing a result.",
        ),
        visual_rules=[
            "compact dashboard layout",
            "8px-or-less panel radius",
            "no marketing hero",
            "raw JSON is secondary to summary content",
        ],
    )
