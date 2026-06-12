# Productize Proposal Mode & Output Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ProductProposal schema, split productize pipeline into proposal+execute phases, persist outputs by paper/product name, and build a three-stage Streamlit UI.

**Architecture:** The productize pipeline is split into `generate_proposals()` (research synthesis + product planning → multiple proposals) and `execute_proposal()` (prototype building → scaffold → evaluation). Reproduce pipeline gains `paper_name` param for output routing. app.py gets three-stage productize UI.

**Tech Stack:** Python 3.12, Streamlit, Pydantic, agents/ pipeline

---

## File Structure

### Files to Modify

| File | Responsibility | Change Summary |
|------|----------------|----------------|
| `schemas/product_schema.py` | Pydantic models for product artifacts | Add `ProductProposal` model |
| `pipeline/reproduce_pipeline.py` | Orchestrates 4 reproduce agents | Add `paper_name` param; route outputs to `outputs/<paper_name>/` |
| `main.py` | Entry point delegating to reproduce pipeline | Pass `paper_name` through to `run_reproduce_pipeline` |
| `pipeline/productize_pipeline.py` | Orchestrates 4 productize agents | Split into `generate_proposals()` + `execute_proposal()` |
| `app.py` | Streamlit UI | Paper name from PDF filename; three-stage productize UI |

### Files to Update

| File | Change |
|------|--------|
| `schemas/__init__.py` | Export `ProductProposal` |
| `pipeline/__init__.py` | Export `generate_proposals`, `execute_proposal` |
| `README.md` | Document proposal flow and output structure |
| `README_ZH.md` | Same in Chinese |

---

### Task 1: Add ProductProposal schema

**Files:**
- Modify: `schemas/product_schema.py`
- Modify: `schemas/__init__.py`

- [ ] **Step 1: Add ProductProposal model to product_schema.py**

Add after `class PrototypePlan(BaseModel):`:

```python
class ProductProposal(BaseModel):
    """One complete product proposal, used in the proposal review stage."""
    product_name: str = ""
    target_user: str = ""
    product_goal: str = ""
    jtbd: str = ""
    opportunities: list[ProductOpportunity] = Field(default_factory=list)
    value_proposition: ValueProposition = Field(default_factory=ValueProposition)
    prd: PRD = Field(default_factory=PRD)
    mvp_scope: MVPScope = Field(default_factory=MVPScope)
    risks: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: Add ProductProposal to schemas/__init__.py exports**

Add `ProductProposal` to the import from `schemas.product_schema` and to `__all__`.

- [ ] **Step 3: Commit**

```bash
git add schemas/product_schema.py schemas/__init__.py
git commit -m "feat(schema): add ProductProposal model for proposal review stage"
```

---

### Task 2: Add paper_name to reproduce pipeline and route outputs

**Files:**
- Modify: `pipeline/reproduce_pipeline.py`
- Modify: `main.py`

- [ ] **Step 1: Update `_save_outputs` and `run_reproduce_pipeline` in reproduce_pipeline.py**

Change lines 84-112: `_save_outputs` accepts optional `output_dir: Path = OUTPUTS_DIR` param.
`run_reproduce_pipeline` accepts optional `paper_name: str = ""`, computes `output_dir = OUTPUTS_DIR / paper_name if paper_name else OUTPUTS_DIR`, and passes it to `_save_outputs`.

Specifically:

```python
def _save_outputs(
    result: PipelineResult,
    repo_scan: dict[str, Any] | None,
    diagnosis_text: str,
    output_dir: Path = OUTPUTS_DIR,
) -> None:
    reproduction_plan = build_reproduction_plan(result)
    result["run_sh"] = build_run_script(repo_scan)
    result["report"] = build_report(result, diagnosis_text)
    for step, writer, content, path in (
        (
            "Failed to save reproduction_plan.md",
            save_markdown,
            reproduction_plan,
            output_dir / "reproduction_plan.md",
        ),
        (
            "Failed to save run.sh",
            save_shell_script,
            result["run_sh"],
            output_dir / "run.sh",
        ),
        (
            "Failed to save report.md",
            save_markdown,
            result["report"],
            output_dir / "report.md",
        ),
    ):
        save_output(result, step, writer, content, path)


def run_reproduce_pipeline(
    pdf_path: str,
    github_url: str = "",
    hardware: str = "Not provided",
    gpu_info: str = "",
    goal: str = "minimal training experiment",
    llm_client: LLMClient | None = None,
    progress_callback: Callable[[str], None] | None = None,
    user_idea: str = "",
    paper_name: str = "",           # NEW
) -> PipelineResult:
```

Add after `client = llm_client or LLMClient()`:

```python
    output_dir = OUTPUTS_DIR / paper_name if paper_name else OUTPUTS_DIR
```

Change the `_save_outputs(...)` call at line 149 and 228 to pass `output_dir=output_dir`.

- [ ] **Step 2: Update main.py to pass paper_name through**

Add `paper_name: str = ""` parameter to `run_paperpilot()`, pass it to `run_reproduce_pipeline()`.

- [ ] **Step 3: Commit**

```bash
git add pipeline/reproduce_pipeline.py main.py
git commit -m "feat(pipeline): add paper_name param to reproduce pipeline for output persistence"
```

---

### Task 3: Split productize pipeline into generate_proposals + execute_proposal

**Files:**
- Modify: `pipeline/productize_pipeline.py`
- Modify: `pipeline/__init__.py`

- [ ] **Step 1: Add `generate_proposals()` function**

New function that runs only ResearchSynthesizer + ProductPlanner, returns `list[ProductProposal]`:

```python
def generate_proposals(
    papers: list[dict[str, Any]],
    target_user: str,
    product_goal: str,
    llm_client: LLMClient,
    user_idea: str = "",
    progress_callback: Callable[[str], None] | None = None,
) -> list[ProductProposal]:
```

Implementation:
1. Create a local `errors` list
2. Run ResearchSynthesizerAgent (same input as today lines 218-235)
3. Run ProductPlannerAgent (same input as today lines 238-256)
4. Build one `ProductProposal` from the ProductPlan. Since ProductPlanner currently returns one plan, we wrap it into a list of 1.
5. For mock variation: if mock mode, generate 2-3 proposals with different product names.

Return `list[ProductProposal]`.

- [ ] **Step 2: Add `execute_proposal()` function**

```python
def execute_proposal(
    proposal: ProductProposal,
    papers: list[dict[str, Any]],
    research_synthesis: dict[str, Any],
    preferred_type: str = "auto",
    repo_path: str = "",
    output_dir: str | Path = "generated_product",
    llm_client: LLMClient | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> ProductResult:
```

Implementation mirrors the second half of today's `run_productize_pipeline()` (from template selection through evaluation), using the selected proposal's data.

Key differences from today:
- `product_spec` is built from the proposal's PRD/MVP (use the existing `_product_plan_to_markdown` but construct a ProductPlan from the proposal)
- Output dir: if `output_dir` is `"generated_product"` (default), derive from `proposal.product_name` → `Path("generated_product") / proposal.product_name`

- [ ] **Step 3: Keep `run_productize_pipeline()` as backward-compatible wrapper**

Refactor `run_productize_pipeline()` to call `generate_proposals()` then `execute_proposal(proposals[0])` so existing callers still work.

- [ ] **Step 4: Update pipeline/__init__.py**

Export `generate_proposals` and `execute_proposal` alongside `run_productize_pipeline`.

- [ ] **Step 5: Commit**

```bash
git add pipeline/productize_pipeline.py pipeline/__init__.py
git commit -m "feat(pipeline): split productize pipeline into generate_proposals and execute_proposal"
```

---

### Task 4: Build three-stage Productize UI

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Initialize session state keys in `main()`**

Add default values for productize session state:

```python
st.session_state.setdefault("productize_stage", "input")
st.session_state.setdefault("productize_proposals", [])
st.session_state.setdefault("productize_selected_proposal", None)
st.session_state.setdefault("productize_result", None)
```

- [ ] **Step 2: Build proposal review UI renderer**

Add function `_render_proposal_review()`:

```python
def _render_proposal_review(proposals: list[dict[str, Any]]) -> None:
    """Display proposals in tabs, let user select one and edit PRD."""
```

Parameters from each proposal in a tab:
- Proposal's `product_name`, `target_user`, `jtbd`
- `opportunities` as a bullet list
- PRD section: problem_statement, core_features (editable text area)
- MVP Scope: must_have, should_have, could_have, wont_have (editable text areas)
- Risks

Each tab has a "Select This Proposal" button. When clicked, store in `productize_selected_proposal` and switch to a sub-stage where the user can edit fields and click "Execute Proposal".

- [ ] **Step 3: Rewrite `_render_productize_mode()` as three-stage**

Structure:

```python
def _render_productize_mode() -> None:
    stage = st.session_state["productize_stage"]

    # Always show input section (collapsible after stage 0)
    st.title("PaperPilot 2.0: Productize Paper")
    with st.expander("Input", expanded=(stage == "input")):
        # Existing input fields: PDF upload, GitHub URL, hardware, target_user,
        # product_goal, preferred_type, user_idea

        if st.button("Generate Proposals", type="primary"):
            # validate, run analysis if needed, call generate_proposals()
            st.session_state["productize_proposals"] = proposals
            st.session_state["productize_stage"] = "review"
            st.rerun()

    if stage == "review":
        proposals = st.session_state["productize_proposals"]
        if not proposals:
            st.error("No proposals were generated.")
            if st.button("Back to input"):
                st.session_state["productize_stage"] = "input"
                st.rerun()
            return

        selected = st.session_state["productize_selected_proposal"]
        if selected is None:
            _render_proposal_review(proposals)
        else:
            # Editing mode: show editable fields + Execute button
            _render_proposal_edit(selected)
    elif stage == "result":
        result = st.session_state.get("productize_result")
        if result:
            _show_productize_result(result)
        if st.button("Start over"):
            st.session_state["productize_stage"] = "input"
            st.session_state["productize_proposals"] = []
            st.session_state["productize_selected_proposal"] = None
            st.session_state["productize_result"] = None
            st.rerun()
```

- [ ] **Step 4: Derive paper_name from PDF filename in reproduce mode**

In `_render_reproduce_mode()`, at line 575 after saving PDF, extract:

```python
paper_name = Path(uploaded_pdf.name).stem
```

Pass it as `paper_name=paper_name` to `run_paperpilot()`.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat(ui): add three-stage Productize UI with proposal review and output persistence"
```

---

### Task 5: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `README_ZH.md`

- [ ] **Step 1: Update Productize Mode section in README.md**

Replace "Productize Mode" usage steps with new flow:
- Step: "Click **Generate Proposals** to see product proposals"
- Step: "Select a proposal and adjust PRD/MVP details"
- Step: "Click **Execute Proposal** to generate the prototype"
- Mention proposals are displayed in tabs, each with full product plan
- Add output persistence note: reproduce outputs go to `outputs/<paper_name>/`, productize outputs to `generated_product/<product_name>/`

- [ ] **Step 2: Update README_ZH.md with same changes in Chinese**

- [ ] **Step 3: Commit**

```bash
git add README.md README_ZH.md
git commit -m "docs(readme): document proposal flow and output persistence"
```
