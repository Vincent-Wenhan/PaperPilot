# Generation Quality and UI Follow-up

## Goal

Further reduce fixed-template behavior in PaperPilot's generated reproduction
projects and generated Productize prototypes.

## Problems Addressed

- A generated reproduction bundle could receive a positive LLM review even when
  deterministic inspection found placeholder-like or thin code.
- `PrototypePlan` contained useful UI planning fields, but the deterministic
  product scaffold mostly rendered the older `image`, `text`, `video`, and
  `file` templates.
- Generated product mock responses did not consistently reflect the selected
  product scenario.

## Implementation

### Reproduction Quality Loop

`pipeline.reproduce_pipeline` now merges deterministic
`assess_implementation_quality()` results into the code review verdict. If the
quality gate fails, PaperPilot forces a `revise` verdict, caps the review score,
and forwards concrete issues and suggestions into the existing revision path.

This keeps LLM reviews useful while ensuring fixed quality checks can still
block low-value generated code.

### Prototype-plan-aware Scaffold

`scaffold_product()` now accepts an optional `prototype_plan` dictionary. The
generated Streamlit app uses:

- `page_structure` for a workflow map,
- `user_inputs` for domain-specific controls,
- `system_outputs` for visible result expectations,
- `mock_result` for planned mock field previews.

The generated adapter also returns the planned `mock_result` in mock mode when
available.

### Prompt and Guideline Updates

The reproduction implementation prompt now asks the agent to behave more like a
small coding agent: infer file architecture, implement central dataflow, add a
safe CLI, and test the implemented behavior.

The prototype builder prompt and Streamlit UI rules now clarify that
`PrototypePlan` fields are implementation-facing and must be concrete enough to
render directly.

## Verification

Focused tests cover:

- deterministic quality gate forcing revision,
- prototype-plan fields appearing in generated app and adapter,
- Productize pipeline compatibility,
- Reproduce graph routing compatibility.
