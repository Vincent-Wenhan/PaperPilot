# Productize Proposal Mode & Output Persistence Design

Date: 2026-06-11

## Summary

Two cohesive enhancements to PaperPilot's Productize workflow: (1) replace the single-shot
product generation with a proposal→select→modify→execute flow, and (2) persist pipeline
outputs by paper/product name so they are never silently overwritten.

---

## Problem

**Current Productize flow** (`app.py:_render_productize_mode` → `run_productize_pipeline`) is a
single button that runs all 4 Productize agents and scaffold in one shot. The user has no
opportunity to see intermediate plans (product opportunities, PRD, MVP scope) and choose
or modify them before code generation.

**Current output storage** (`pipeline/reproduce_pipeline.py:_save_outputs`) writes three files
(`reproduction_plan.md`, `run.sh`, `report.md`) directly into `outputs/`, overwriting the
previous run. There is no way to keep results from multiple papers or multiple runs.

---

## Design

### 1. Output Persistence (`outputs/` by paper/product name)

#### 1.1 Reproduce Mode

`reproduce_pipeline.run_reproduce_pipeline()` gains an optional `paper_name: str = ""`
parameter. When provided, output files are written to:

```
outputs/<paper_name>/
├── reproduction_plan.md
├── run.sh
└── report.md
```

When omitted (backward-compatible default), the current `outputs/` root behaviour is preserved.

The paper name is derived from the uploaded PDF filename (basename without extension).
This derivation happens in `app.py:_render_reproduce_mode()` where the PDF is saved, and
is passed through to the pipeline.

#### 1.2 Productize Mode

`productize_pipeline` derives `product_name` from the **selected** `ProductProposal.product_name`
(a new field in the schema — see §2.1). Outputs are written to:

```
outputs/products/<product_name>/
├── product_spec.md
├── prototype_plan.json
├── inspection.json
└── evaluation.json
```

The `outputs/products/` prefix avoids collision with reproduce-mode directories.

#### 1.3 Backward Compatibility

- Reproduce: default `paper_name=""` → writes to `outputs/` as today.
- Productize: no old behaviour to preserve (the output dir was `generated_product/` only).

### 2. Productize Proposal Flow

#### 2.1 New Schema: `ProductProposal`

```python
class ProductProposal(BaseModel):
    product_name: str           # Used as output dir name
    target_user: str
    product_goal: str
    jtbd: str
    opportunities: list[ProductOpportunity]
    selected_opportunity: ProductOpportunity
    value_proposition: ValueProposition
    prd: PRD
    mvp_scope: MVPScope
    risks: list[str]
```

#### 2.2 Pipeline Split

`productize_pipeline` is split into two exposed functions:

| Function | Stages Run | Returns |
|----------|------------|---------|
| `generate_proposals(llm_client, papers, target_user, product_goal, user_idea)` | ResearchSynthesizer + ProductPlanner | `list[ProductProposal]` |
| `execute_proposal(proposal: ProductProposal, preferred_type, repo_path, output_dir, llm_client)` | PrototypeBuilder → scaffold → ProductEvaluator | `ProductResult` (full dict) |

#### 2.3 UI Flow (`app.py`)

The Productize Mode is restructured into three stages, with session state tracking the current stage:

```
Stage 0: Input
  [PDF upload, GitHub URL, target user, product goal, preferred type, user idea]
  ↓ when "Generate Proposals" clicked
Stage 1: Proposal Review
  Tabs — one per ProductProposal
  Each tab shows:
    - product_name, target_user, jtbd
    - PRD (problem, core features, user flow)
    - MVP Scope (must/should/could/won't)
    - Risks
    - "Select This Proposal" button
  When a proposal is selected:
    - User can edit PRD.core_features text, MVP lists in text areas
    - "Execute Proposal" button
  ↓ when "Execute Proposal" clicked
Stage 2: Generated Product
  [same as today's _show_productize_result]
```

Session state keys:
- `productize_proposals`: `list[ProductProposal]` — cached proposals
- `productize_selected_proposal`: `ProductProposal | None` — the chosen + modified proposal
- `productize_stage`: `"input" | "review" | "result"`

#### 2.4 Edge Cases

| Case | Behaviour |
|------|-----------|
| No proposals generated (all stages fail) | Show error, stay in Stage 0 |
| User re-clicks "Generate Proposals" | Clear old proposals and regenerate |
| User navigates away from Productize tab | All session state preserved (Streamlit default) |
| Only one proposal generated | Still show in tabs with single tab — no auto-select |
| Modified PRD has empty fields | Validate non-empty before execution |
| Product name contains special chars | Sanitise to `[a-zA-Z0-9_-]` for directory name |

---

## Files Changed

| File | Change |
|------|--------|
| `schemas/product_schema.py` | Add `ProductProposal` model |
| `pipeline/reproduce_pipeline.py` | Add `paper_name` param; route outputs to `outputs/<paper_name>/` |
| `pipeline/productize_pipeline.py` | Split into `generate_proposals()` + `execute_proposal()`; derive product_name from proposal |
| `app.py` | Three-stage Productize UI; pass paper_name from PDF filename |
| `README.md` | Document new Productize proposal flow and output structure |
| `README_ZH.md` | Same, in Chinese |
| `docs/DEVELOPMENT.md` | Update architecture description if needed |

---

## Testing

- **Unit**: new `ProductProposal` schema validation
- **Unit**: `generate_proposals` returns correct shape
- **Unit**: output path routing with `paper_name`
- **UI**: manual verification of the three-stage flow in Streamlit
