# Generation Protocol and Workbench Design

## Goal

Deepen PaperPilot's generation quality by introducing explicit intermediate
generation protocols, then use those protocols to improve both generated
reproduction projects and generated Productize UI. The change keeps the
existing mock-first safety model, LangGraph architecture, and deterministic
filesystem writers.

## Current Problems

PaperPilot has already improved generated code quality checks and made
`PrototypePlan` influence generated product apps. The remaining weakness is
that generation still depends too much on broad prompts and string templates.

Observed issues:

- Reproduce Mode asks the implementation agent to produce files directly,
  without first giving it a concrete project architecture contract.
- The deterministic quality gate can force revision, but it cannot yet compare
  generated files against an expected blueprint.
- Productize Mode has a richer `PrototypePlan`, but the app builder still
  infers controls from short strings and template type.
- PaperPilot's host UI still exposes many raw artifacts before explaining the
  generated project or prototype as a product workflow.

## Design Principles

- Keep LLM agents advisory and bounded by schemas.
- Keep all file writes behind deterministic builders.
- Prefer structured generation contracts over larger prompts.
- Make generated artifacts inspectable before they are runnable.
- Keep Streamlit for this phase to avoid front-end stack expansion.
- Preserve existing public result keys. New protocol fields must be additive
  unless a test documents an intentional compatibility change.

## Reproduce Generation Protocol

Add an `ImplementationBlueprint` schema in `schemas/reproduction_schema.py`.

The blueprint describes the expected generated project before the
implementation agent writes files:

- `project_name`: safe generated project name.
- `objective`: one-sentence goal for the generated reproduction project.
- `architecture_summary`: concise explanation of the generated project shape.
- `files`: planned files with path, responsibility, required symbols, and test
  relevance.
- `core_dataflow`: ordered synthetic smoke-test dataflow steps.
- `required_entrypoints`: safe commands such as `python main.py --smoke-test`.
- `quality_requirements`: concrete checks the implementation must satisfy.
- `forbidden_patterns`: unsafe or low-quality patterns to reject.

Add a deterministic builder in `tools/implementation_blueprint.py`. It derives
a conservative blueprint from:

- `PaperUnderstanding.method_modules`
- `PaperUnderstanding.end_to_end_dataflow`
- `RepositoryUnderstanding.detected_framework`
- `ReproductionPlan.implementation_strategy`
- hardware and goal inputs

The first implementation should not try to infer every possible research
domain. It should produce a reliable minimal architecture:

- `README.md`
- `config.py`
- one or more method modules such as `model.py`, `dataflow.py`, or `metrics.py`
- `main.py`
- `tests/test_dataflow.py`
- `requirements.txt`

Names may vary when evidence clearly supports domain-specific modules, but the
builder must stay deterministic.

## Reproduce Pipeline Integration

Update Reproduce graph state and result dictionaries with:

- `implementation_blueprint`
- `blueprint_quality`

Pipeline order becomes:

```text
Research Understanding
Repository Understanding
Reproduction Planning
Implementation Blueprint
Implementation Bundle
Code Quality + Blueprint Coverage
Code Review / Revision
Materialization
Sandbox Verification
Diagnosis and Outputs
```

The Reproduction Implementation Agent receives the blueprint in its structured
input. The prompt should tell the agent to implement the blueprint unless paper
evidence makes a deviation necessary, and deviations must be explained in the
bundle summary or assumptions.

Enhance `tools.code_quality.assess_implementation_quality()` or add a nearby
helper so quality evaluation can compare `ImplementationBundle` to
`ImplementationBlueprint`:

- planned file missing,
- required symbol missing,
- test file missing,
- smoke-test command not represented,
- generated files not mentioned in README,
- low implementation complexity relative to the blueprint.

If blueprint coverage fails, `_merge_quality_into_review()` continues to force
revision through the existing review path.

## Product UI Generation Protocol

Add a `ProductUISpec` schema in `schemas/product_schema.py`.

The spec is derived from `ProductPlan` and `PrototypePlan`, then consumed by
the deterministic scaffold. It should include:

- `layout_mode`: one of `workflow_dashboard`, `review_console`, or
  `analysis_workspace`.
- `page_sections`: ordered named sections.
- `input_controls`: structured controls with id, label, control type, default,
  options, help text, and whether the control is required.
- `result_components`: metrics, summary cards, evidence lists, tables, and
  downloadable artifacts.
- `mock_result_schema`: expected mock output keys and user-facing labels.
- `states`: empty, loading, success, and error state copy.
- `visual_rules`: compact density, restrained panels, 8px-or-less radius, and
  no marketing hero.

Add a deterministic builder in `productize/ui_spec.py`. The builder normalizes
weak or sparse `PrototypePlan` output into a usable spec:

- threshold-like inputs become sliders,
- mode/category inputs become select boxes,
- free context fields become text inputs or text areas,
- mock result fields become visible result components,
- limitations and adapter boundary become evidence/limits content.

## Productize Scaffold Integration

Update `scaffold_product()` to accept `ui_spec` while keeping
`prototype_plan` optional for backward compatibility.

The generated `app.py` should be rendered from `ProductUISpec`, not from a
flat string list:

- sidebar settings remain visible,
- task setup controls are generated from `input_controls`,
- primary template input remains image/text/video/file aware,
- result tabs are generated from `result_components`,
- empty/error/loading states are explicit,
- mock result preview and output labels are product-specific.

The generated `adapter.py` continues to default to `mock_mode=True` and never
imports, downloads, trains, or executes the analyzed repository.

The product inspector should report `ui_spec_coverage` with booleans for:

- structured controls rendered,
- result components rendered,
- state copy rendered,
- mock schema visible,
- run command present,
- syntax valid.

## Host UI Workbench

Improve the Streamlit host UI without replacing Streamlit in this phase.

### Reproduce Result Workbench

Add a concise generated-project summary before raw file listings:

- generated repository path,
- implementation model,
- blueprint file count,
- generated file count,
- quality score,
- blueprint coverage status,
- smoke-test command.

Add a Blueprint tab or section that renders:

- planned files and responsibilities,
- required symbols,
- synthetic dataflow,
- quality requirements.

Raw code remains available in expanders after the summary.

### Productize Result Workbench

Add a product prototype summary before debug artifacts:

- product name,
- target user,
- output directory,
- template type,
- UI spec coverage status,
- generated file count,
- run command.

Add an App Structure tab that renders:

- page sections,
- input controls,
- result components,
- states,
- adapter boundary.

Raw JSON remains available under a debug or raw section, not as the primary
review surface.

## Error Handling and Compatibility

- If blueprint construction fails, record a stage-qualified error and use a
  conservative fallback blueprint.
- If UI spec construction fails, record an error and use a conservative
  fallback UI spec.
- Existing result keys remain stable. New keys are additive.
- Existing callers of `scaffold_product()` continue to work without `ui_spec`.
- Generated products remain mock-first.
- Static inspection never launches Streamlit.

## Testing Strategy

Use test-first implementation.

Reproduce tests:

- blueprint builder creates a multi-file architecture from method modules.
- sparse paper evidence still produces a conservative fallback blueprint.
- quality assessment flags missing blueprint files and symbols.
- accepted code review is forced to revision when blueprint coverage fails.
- Reproduce graph/result includes blueprint metadata when code generation is on.

Productize tests:

- UI spec builder converts prototype controls into typed controls.
- fallback UI spec works with sparse prototype plans.
- scaffold renders controls, result components, state copy, and mock schema.
- inspector reports UI spec coverage markers.
- Productize pipeline passes UI spec into scaffold and result output.

Host UI helper tests:

- generated project summary returns scan-friendly fields.
- product prototype summary includes UI spec coverage.
- raw JSON remains available but is not required for summary rendering.

Full verification:

```bash
conda run -n paperpilot python -m pytest -q
```

## Delivery Plan

Implementation should happen in focused commits on
`codex/product-quality-ui-upgrade`:

1. Add schemas and deterministic blueprint/UI spec builders with tests.
2. Connect Reproduce blueprint and quality coverage to the pipeline.
3. Connect ProductUISpec to product scaffold and inspection.
4. Improve host UI summaries for Reproduce and Productize.
5. Update prompts, guidelines, README, README_ZH, and development docs.

All commits should follow Conventional Commits.
