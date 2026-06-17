# Product Quality and UI Upgrade Design

## Goal

Improve PaperPilot's generated reproduction code, generated product prototypes,
and Productize Mode UI without changing the mock-first safety model or replacing
the existing LangGraph pipeline.

## Current Problems

- Generated reproduction projects can still look like generic scaffolds when the
  model output is weak or fallback paths are used.
- Product prototypes are built from four fixed Streamlit templates, so different
  papers often produce similar apps with a single input and raw JSON output.
- Productize Mode exposes many intermediate artifacts as JSON, which is useful
  for debugging but hard to review as a product workflow.

## Approach

PaperPilot will keep LLM agents advisory and keep all filesystem writes behind
deterministic builders. The upgrade adds deterministic quality gates and richer
UI generation rules at those boundaries.

### Reproduction Code Quality

Add a `tools.code_quality` module that scores an `ImplementationBundle` before
or after materialization. The checker is deterministic and inspects only the
generated file metadata and source text. It reports:

- overall score from 1 to 5,
- file count, Python file count, test count, and README/config/entrypoint
  presence,
- blocking issues such as placeholder bodies, generic mock-only wording,
  missing tests, missing README, or no meaningful Python implementation,
- improvement suggestions that can be shown in the UI and passed to future
  review loops.

This does not execute untrusted generated code and does not loosen existing path
or network safety checks.

### Product Prototype Generation

Extend the deterministic product scaffold so `app.py` is generated from product
context, not only template type. The generated app should include:

- product-specific page title,
- sidebar controls for mock mode, confidence threshold, and output verbosity,
- a task setup area with inputs tailored to image, text, video, or file mode,
- result summary metrics,
- evidence, assumptions, limitations, and export tabs,
- custom CSS with restrained dashboard styling.

The adapter stays mock-first and does not import or run the analyzed repository.

### Productize UI

Improve result rendering by adding a concise generated product summary:

- output directory,
- scaffold status,
- static inspection status,
- generated file count,
- run command for the actual generated product directory.

Existing detailed tabs remain available, but the first screen should be easier
to scan.

### Prompts and Guidelines

Strengthen `prototype_builder_prompt.txt` and `guidelines/streamlit_ui_rules.md`
so the agent plans product-specific information architecture, controls, result
views, empty/error states, and mock output structure. The prompt should make
clear that a prototype is a usable workflow, not a JSON demo.

## Testing

- Add unit tests for `assess_implementation_quality`.
- Extend product scaffold tests to assert product-specific titles, layout
  controls, tabs, and run commands.
- Extend product inspector tests to report layout markers.
- Keep existing scaffold, syntax, and mock-mode checks passing.

## Delivery

Work happens on `codex/product-quality-ui-upgrade`, with focused commits and a
push to GitHub when verification passes.
