"""Build structured UI specs for generated Productize prototypes."""

from __future__ import annotations

import re

from schemas.product_schema import (
    ProductContract,
    ProductIOContract,
    ProductPlan,
    ProductSafetyContract,
    ProductUXContract,
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


def _label_from_field(field_id: str) -> str:
    return field_id.replace("_", " ").strip().title()


def _infer_input_type(template_type: str, controls: list[str]) -> str:
    normalized = template_type.lower()
    if normalized in {"image", "text", "video", "file"}:
        return normalized
    joined = " ".join(controls).lower()
    matched = [
        kind
        for kind in ("image", "text", "video", "file")
        if kind in joined or ("upload" in joined and kind == "file")
    ]
    return matched[0] if len(set(matched)) == 1 else "mixed"


def build_product_contract(
    product_plan: ProductPlan,
    prototype_plan: PrototypePlan,
) -> ProductContract:
    """Derive an executable product contract from PRD and prototype intent."""
    product_name = product_plan.prd.product_name or product_plan.selected_product or "Generated Product"
    input_labels = _nonblank(prototype_plan.user_inputs) or [
        f"{prototype_plan.template_type} input",
        "Decision context",
    ]
    output_labels = _nonblank(prototype_plan.system_outputs) or [
        "Structured mock result",
        "Downloadable JSON",
    ]
    used_input_fields: set[str] = set()
    input_fields = [
        _unique_id(_slug(label, f"input_{index}"), used_input_fields)
        for index, label in enumerate(input_labels[:6], 1)
    ]
    used_output_fields: set[str] = set()
    output_fields = [
        _unique_id(_slug(label, f"output_{index}"), used_output_fields)
        for index, label in enumerate(output_labels[:8], 1)
    ]
    mock_result = dict(prototype_plan.mock_result or {})
    for field in output_fields:
        mock_result.setdefault(field, "")
    example_input = {
        field: (
            0.65
            if any(word in field for word in ("threshold", "score", "confidence"))
            else f"Example {field.replace('_', ' ')}"
        )
        for field in input_fields
    }
    return ProductContract(
        product_name=product_name,
        target_user=(
            ", ".join(product_plan.prd.target_users)
            or (
                product_plan.opportunities[0].target_user
                if product_plan.opportunities
                else ""
            )
        ),
        job_to_be_done=product_plan.jtbd,
        io=ProductIOContract(
            input_type=_infer_input_type(prototype_plan.template_type or "", input_labels),
            input_fields=input_fields,
            output_fields=output_fields,
            example_input=example_input,
            example_output=mock_result,
        ),
        ux=ProductUXContract(
            primary_user_action="Run mock analysis",
            required_controls=input_fields,
            required_result_cards=output_fields,
            empty_state=f"Provide input to start {product_name}.",
            loading_state="Running safe mock analysis.",
            error_state="Mock workflow failed before producing a result.",
        ),
        safety=ProductSafetyContract(
            forbidden_claims=[
                "guaranteed SOTA",
                "fully reproduces",
                "clinically validated",
                "production ready",
            ],
            required_disclaimers=["mock mode"],
            mock_mode_boundary=(
                "Mock mode demonstrates product workflow and does not claim full paper reproduction."
            ),
        ),
        acceptance_tests=[
            "Render every required control.",
            "Submit example input and show every required output field.",
            "Avoid forbidden claims and clearly state mock-mode limits.",
        ],
    )


def build_product_ui_spec(
    product_plan: ProductPlan,
    prototype_plan: PrototypePlan,
    product_contract: ProductContract | dict[str, object] | None = None,
) -> ProductUISpec:
    """Normalize ProductPlan and PrototypePlan into renderable UI structure."""
    product_name = product_plan.prd.product_name or product_plan.selected_product or "Generated Product"
    has_explicit_contract = product_contract is not None
    contract = (
        ProductContract.model_validate(product_contract)
        if has_explicit_contract
        else build_product_contract(product_plan, prototype_plan)
    )
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
    controls: list[UIControl] = []
    for index, field in enumerate(contract.ux.required_controls[:6], 1):
        label = (
            _label_from_field(field)
            if has_explicit_contract
            else input_labels[index - 1] if index - 1 < len(input_labels) else _label_from_field(field)
        )
        control = _control_for_label(label, index, set())
        controls.append(
            UIControl(
                **{
                    **control.model_dump(),
                    "control_id": _unique_id(field, used_control_ids),
                    "label": label,
                    "required": True,
                }
            )
        )
    mock_schema = {
        str(key): str(type(value).__name__)
        for key, value in (contract.io.example_output or prototype_plan.mock_result or {"summary": "mock result"}).items()
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
    result_fields = contract.ux.required_result_cards or contract.io.output_fields
    for index, output in enumerate(result_fields, 1):
        output_label = (
            _label_from_field(output)
            if has_explicit_contract
            else system_outputs[index - 1] if index - 1 < len(system_outputs) else _label_from_field(output)
        )
        result_components.append(
            ResultComponent(
                component_id=_unique_id(_slug(output_label, f"result_{index}"), used_component_ids),
                label=output_label,
                component_type="summary",
                source_key=output if has_explicit_contract else "result",
                description=output_label,
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
