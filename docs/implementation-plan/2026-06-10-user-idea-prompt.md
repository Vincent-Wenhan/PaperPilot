# Custom User Idea / Prompt — Design Document

> 2026-06-10

## Problem

Users may have specific ideas about what kind of product they want to build from a paper (Productize Mode), or particular concerns / areas of focus they want the reproduction plan to address (Reproduce Mode). Currently both modes offer only structured fields (goal selector, hardware, target user, product goal) with no way for the user to express free-form intent.

Adding an optional free-text "User Idea" field lets users guide the LLM agents with their own thoughts without being constrained to predefined fields.

## Design

Add an optional `st.text_area` in both modes' input sections:

| Mode | Field Label | Default | Placement |
|---|---|---|---|
| Reproduce | "Additional Notes (optional)" | `""` | Below the goal selector |
| Productize | "Product Idea (optional)" | `""` | Below the Product Goal text area |

When non-empty, the value is passed into the relevant agent `input_data` dicts so the LLM sees it as additional context. Empty values are omitted or passed as empty strings (agents already handle missing/empty fields gracefully since BaseAgent serialises the full dict to JSON).

## Data Flow

### Reproduce Mode

```
UI → st.session_state["reproduce_user_idea"]
    ↓
run_paperpilot(..., user_idea="...")
    ↓
Passed into agent input_data dicts:
  - PaperReaderAgent input_data (appended to paper_text as extra note)
  - MethodExtractorAgent input_data
  - ExperimentAgent input_data (experiment_context)
  - ReportAgent input_data (report_context)
```

### Productize Mode

```
UI → st.session_state["productize_user_idea"]
    ↓
run_productize_pipeline(..., user_idea="...")
    ↓
Passed into agent input_data dicts:
  - ProductOpportunityAgent input_data
  - ProductDesignerAgent input_data
```

## Files to Change

### `docs/implementation-plan/2026-06-10-user-idea-prompt.md`
- This design document.

### `app.py`
- **Reproduce mode** (`_render_reproduce_mode()`): Add `st.text_area("Additional Notes (optional)")` after the goal selector. Store in `st.session_state["reproduce_user_idea"]`. Pass to `run_paperpilot(user_idea=...)`.
- **Productize mode** (`_render_productize_mode()`): Add `st.text_area("Product Idea (optional)")` after product goal. Store in `st.session_state["productize_user_idea"]`. Pass to `run_productize_pipeline(user_idea=...)`.

### `main.py`
- `run_paperpilot()`: Accept `user_idea: str = ""` parameter.
- Include `user_idea` in the input_data dicts for: PaperReaderAgent, MethodExtractorAgent, ExperimentAgent (experiment_context), ReportAgent (report_context).

### `productize/product_pipeline.py`
- `run_productize_pipeline()`: Accept `user_idea: str = ""` parameter.
- Include `user_idea` in both ProductOpportunityAgent and ProductDesignerAgent input_data dicts.

## Non-Goals

- No UI-specific LLM response fields (we don't display "your idea was received" messages).
- No validation of idea content.
- No effect on deterministic stages (repo clone, scan, runner, scaffold, tester).
- No change to prompts or agent logic — agents already forward the full input dict to the LLM, so the new field is automatically visible.

## Verification

1. Launch app, switch to Reproduce mode, fill in "Additional Notes", run pipeline — confirm output mentions the custom note (mock mode returns fixed text, but confirm no crash).
2. Switch to Productize mode, fill in "Product Idea", generate prototype — confirm no crash.
3. Leave both fields empty — confirm existing behavior unchanged.
4. Run existing test suite to confirm no regressions.
