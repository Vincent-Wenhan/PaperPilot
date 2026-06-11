# Agent Collaboration & Human-in-the-Loop Improvement Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 4 human-in-the-loop confirmation nodes to the existing pipeline so users validate agent output before passing it to downstream agents, reducing waste from cascaded misunderstandings.

**Architecture:** Introduce a `PipelineHITL` context object that stores HITL state per stage and exposes a `confirm(stage_key, rendered_content) -> bool` protocol. Pipeline functions accept a `hitl: PipelineHITL | None` parameter — when `None` (default), all confirmation steps are skipped (backward-compatible). Each HITL node renders structured agent output as Markdown, waits for user confirmation, and either proceeds (confirms) or records a rejection error and continues with a fallback.

**Tech Stack:** Python 3.12+, Streamlit, Pydantic, existing renderers.

---

## Problem

The current pipeline is fully serial with no user validation between agents:

```
A → B → C → D
```

If A produces a flawed output, B, C, and D amplify the error. Users discover the problem only at the end. HITL nodes let users catch errors early, when correcting a single upstream agent costs far less than re-running everything.

## HITL Nodes

Four confirmation points are added, two per mode:

| # | Mode | After Agent | What User Sees | Fallback on Reject |
|---|------|-------------|----------------|--------------------|
| 1 | Reproduce | ResearchUnderstandingAgent | Paper summary (title, task, problem, contributions, method modules) | Record rejection error, continue with `paper_info="[Rejected by user]"` |
| 2 | Reproduce | ReproductionPlannerAgent | Experiment plan (minimal reproduction steps, full reproduction, environment plan) | Same — record error, continue |
| 3 | Productize | ResearchSynthesizerAgent | Capability cards + capability map + composition plan | Record rejection error, continue with empty synthesis |
| 4 | Productize | PrototypeBuilderAgent (before scaffold) | Prototype plan (page structure, inputs, outputs, mock result, adapter boundary) | Record rejection error, skip scaffold, mark product as incomplete |

### Confirmation Protocol

Each HITL node follows the same pattern:

1. Pipeline renders agent output to Markdown (reuse existing `render_*` functions).
2. If `hitl` context is `None` → skip, continue immediately (backward-compatible).
3. Otherwise, call `hitl.request_confirmation(stage_key, title, markdown_content)` — this returns `True` (confirmed) or `False` (rejected).
4. If confirmed → continue normally.
5. If rejected → record rejection in `result["errors"]`, set a sentinel value on the relevant field, continue.

### Handling "Reject + Retry"

When a user rejects a stage, they may want to retry with corrected input. The HITL context supports this:

- `hitl.request_confirmation()` returns `True`, `False`, or `"retry"`.
- On `"retry"`: the pipeline re-invokes the same agent with an additional `user_correction` field in its input dict, containing the user's free-text correction. The agent regenerates its output incorporating the feedback.

This is implemented in the Streamlit UI as three buttons per HITL modal: "Confirm", "Reject (skip)", and "Retry with feedback".

## Architecture

### PipelineHITL Context

```
┌─────────────────────────────────────────────┐
│              PipelineHITL                    │
├─────────────────────────────────────────────┤
│ + stages: dict[str, HITLState]               │
│ + on_confirm(key, title, content) -> bool    │
│   | "retry"                                  │
│ + record_rejection(key, reason: str)         │
│ + set_correction(key, text: str)             │
│ + is_pending(key) -> bool                    │
└─────────────────────────────────────────────┘
```

The `PipelineHITL` class is defined in a new file `pipeline/hitl_context.py`. It:

- Stores per-stage state (pending/confirmed/rejected/retry).
- Delegates the actual UI interaction to a callback (`on_confirm`), so the same class works with Streamlit or CLI.
- Accumulates user corrections for retry.

### Streamlit Integration

`app.py` creates a `StreamlitHITL` subclass that overrides `on_confirm` to render a modal/overlay using `st.markdown` + `st.columns` buttons.

```python
class StreamlitHITL(PipelineHITL):
    def on_confirm(self, key: str, title: str, content: str) -> str | None:
        """Show a confirmation dialog. Returns 'confirm', 'reject', or 'retry'."""
        st.markdown(f"### {title}")
        st.markdown(content)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(f"Confirm", key=f"hitl_{key}_confirm"):
                return "confirm"
        with col2:
            feedback = st.text_area("Feedback for retry", key=f"hitl_{key}_feedback")
            if st.button(f"Retry with feedback", key=f"hitl_{key}_retry"):
                self.set_correction(key, feedback)
                return "retry"
        with col3:
            if st.button(f"Reject & Continue", key=f"hitl_{key}_reject"):
                self.record_rejection(key, "User rejected this stage.")
                return "reject"
        return None  # Still waiting
```

### Pipeline Modification

#### Reproduce pipeline (`pipeline/reproduce_pipeline.py`)

```
run_reproduce_pipeline(pdf_path, github_url, ..., hitl: PipelineHITL | None = None):
    ...
    # Stage 1: ResearchUnderstanding
    research = ResearchUnderstandingAgent(...).run_structured(research_input)
    if hitl:
        content = render_research_summary(research)
        result = hitl.request_confirmation("research", "Paper Summary", content)
        if result == "retry":
            research_input["user_correction"] = hitl.get_correction("research")
            research = ResearchUnderstandingAgent(...).run_structured(research_input)
        elif result == "reject":
            _record_error(result, "HITL: Research Understanding", "Rejected by user")
            # Continue with existing output but mark it
    ...
    # Stage 2: RepositoryUnderstanding (no HITL — repo scan is deterministic)
    ...
    # Stage 3: ReproductionPlanner
    plan = ReproductionPlannerAgent(...).run_structured(planner_input)
    if hitl:
        content = render_environment_plan(plan) + "\n\n" + render_experiment_plan(plan)
        result = hitl.request_confirmation("experiment", "Experiment Plan", content)
        # Same retry/reject handling as above
    ...
```

#### Productize pipeline (`pipeline/productize_pipeline.py`)

```
generate_proposals(papers, ..., hitl: PipelineHITL | None = None):
    ...
    synthesis = ResearchSynthesizerAgent(...).run_structured(...)
    if hitl:
        content = render_capability_cards(synthesis)  # New renderer
        result = hitl.request_confirmation("capabilities", "Capability Cards", content)
        # retry/reject handling
    ...
    product_plan = ProductPlannerAgent(...).run_structured(...)
    ...

execute_proposal(proposal, ..., hitl: PipelineHITL | None = None):
    ...
    prototype_plan = PrototypeBuilderAgent(...).run_structured(...)
    if hitl:
        content = render_prototype_plan(prototype_plan)  # reuse existing _prototype_plan_to_markdown
        result = hitl.request_confirmation("prototype", "Prototype Plan", content)
        if result == "reject":
            _record_error(...)
            # Skip scaffold
            return result
    # Only proceed to scaffold if confirmed or no HITL
    scaffold_product(...)
    ...
```

### New Renderer

A lightweight `pipeline/hitl_renderers.py` adds a function to render `ResearchSynthesis` for the Capability Cards HITL node:

```python
def render_capability_cards(synthesis: ResearchSynthesis) -> str:
    """Render capability cards for HITL confirmation."""
    lines = ["# Capability Cards"]
    for card in synthesis.capability_cards:
        lines.extend([
            f"## {card.paper_title}",
            f"**Capabilities:**",
            *[f"- {cap}" for cap in card.capabilities],
            "",
        ])
    lines.append("## Capability Map")
    lines.append(synthesis.capability_map.get("summary", ""))
    lines.append("")
    lines.append("## Composition Plan")
    lines.append(synthesis.composition_plan.get("composition_rationale", ""))
    return "\n".join(lines)
```

### Session State in Streamlit

The `StreamlitHITL` stores HITL state in `st.session_state` so re-renders preserve the confirmation dialog until the user acts:

```python
# In session state:
# "hitl_context": StreamlitHITL instance (one per pipeline run)
# "hitl_states": dict[str, HITLState] — persisted within a stage
```

### Backward Compatibility

- `run_reproduce_pipeline()` and `run_productize_pipeline()` accept `hitl=None` by default → no behavioral change.
- `generate_proposals()` and `execute_proposal()` accept `hitl=None` by default.
- All existing tests and callers continue to work unchanged.
- The output result dict gains an `"hitl_rejections"` list when HITL is active, but this is absent/empty for existing callers.

### Streamlit UI Changes (`app.py`)

The main changes are in `_render_reproduce_mode()` and `_render_productize_mode()`:

1. Before calling pipeline functions, create a `StreamlitHITL` if the user has HITL enabled (a new sidebar toggle "Enable HITL").
2. The HITL confirmation dialog replaces `st.status()` or `st.spinner()` — the pipeline pauses, shows content, waits for button press.
3. The pipeline is called inside a loop that re-checks HITL state: `hitl.is_pending("research")` blocks until the user acts, then continues.

This requires running the pipeline in a **stepwise fashion** within Streamlit. The pattern:

```python
if st.button("Analyze"):
    hitl = StreamlitHITL()
    st.session_state["hitl"] = hitl
    st.session_state["pipeline_stage"] = "research"
    # Start first stage

# Check HITL state on each rerun
hitl = st.session_state.get("hitl")
if hitl and hitl.is_pending("research"):
    # Show the confirmation (handled by on_confirm in StreamlitHITL)
    pass
elif hitl and hitl.is_pending("experiment"):
    # Show experiment plan confirmation
    pass
```

A simpler alternative: run the full pipeline in a background thread with a callback-based HITL that blocks until the user clicks a button (signaled via `st.session_state`). This avoids the complex stepwise state machine.

**Recommendation:** Use the simpler callback-semaphore pattern. The pipeline is synchronous; HITL confirmation is a blocking call that polls `st.session_state` keys. This keeps the pipeline code linear.

### Semaphore Pattern for Synchronous Pipeline

```python
class StreamlitHITL(PipelineHITL):
    def on_confirm(self, key, title, content):
        # Store content for display
        st.session_state[f"hitl_pending_{key}"] = {"title": title, "content": content}
        # Wait for user action (Streamlit reruns until button clicked)
        while st.session_state.get(f"hitl_pending_{key}"):
            st.rerun()  # This raises st.scriptrunner.StopException
            # On rerun, the UI shows the dialog and reads button clicks
        # After button click, the key is cleared and on_confirm returns
        return st.session_state.pop(f"hitl_result_{key}", "reject")
```

## Files to Create

- `pipeline/hitl_context.py` — `PipelineHITL` base class + `HITLState` dataclass
- `pipeline/hitl_renderers.py` — `render_capability_cards()` for ResearchSynthesis

## Files to Modify

- `pipeline/reproduce_pipeline.py` — Add `hitl` param, insert 2 confirmation points
- `pipeline/productize_pipeline.py` — Add `hitl` param to `generate_proposals()` and `execute_proposal()`, insert 2 confirmation points
- `app.py` — Add HITL toggle in sidebar, create `StreamlitHITL`, rerun logic

## Files NOT Modified

- `agents/*` — Agents are unchanged; they only receive input and return output
- `schemas/*` — No new schemas needed
- `prompts/*` — Prompts unchanged
- `README.md`, `README_ZH.md` — No new user-facing features that change workflow

## Implementation Plan

Implementation will be split into 5 tasks:

1. **PipelineHITL base class** — Create `pipeline/hitl_context.py` with `HITLState` dataclass and `PipelineHITL` base class with `request_confirmation()`, `get_correction()`, `record_rejection()`, `is_pending()`.
2. **HITL renderers** — Create `pipeline/hitl_renderers.py` with `render_capability_cards()`.
3. **Reproduce pipeline HITL** — Add `hitl` param to `run_reproduce_pipeline()`, insert 2 confirmation points (after ResearchUnderstanding, after ReproductionPlanner).
4. **Productize pipeline HITL** — Add `hitl` param to `generate_proposals()` and `execute_proposal()`, insert 2 confirmation points (after ResearchSynthesizer, after PrototypeBuilder).
5. **Streamlit UI** — Add `StreamlitHITL` class, HITL toggle, rerun logic in `_render_reproduce_mode()` and `_render_productize_mode()`.
