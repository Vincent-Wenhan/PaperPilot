# Product Quality UI Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic generated-code quality checks and richer product prototype UI generation.

**Architecture:** Keep the existing LangGraph agents and mock-first builders. Add quality analysis as a deterministic tool and upgrade scaffold rendering to consume product context while preserving safety checks.

**Tech Stack:** Python 3.12, Pydantic schemas, Streamlit, unittest/pytest-compatible tests.

---

### Task 1: Reproduction Code Quality Checker

**Files:**
- Create: `tools/code_quality.py`
- Test: `tests/test_code_quality.py`

- [ ] Write tests for low-quality placeholder bundles and richer bundles.
- [ ] Implement `assess_implementation_quality(bundle)` with deterministic metrics, score, issues, and suggestions.
- [ ] Run `python -m pytest tests/test_code_quality.py -q`.

### Task 2: Product Scaffold UI Upgrade

**Files:**
- Modify: `productize/product_templates.py`
- Modify: `productize/product_scaffold.py`
- Modify: `productize/product_tester.py`
- Test: `tests/test_product_scaffold.py`

- [ ] Extend tests to require product-specific title, sidebar controls, tabs, layout markers, and correct run command.
- [ ] Update generated `app.py` source to render a richer mock-first workflow.
- [ ] Update scaffold README and inspector layout checks.
- [ ] Run `python -m pytest tests/test_product_scaffold.py -q`.

### Task 3: Pipeline and UI Surfacing

**Files:**
- Modify: `pipeline/reproduce_pipeline.py`
- Modify: `ui/shared.py`
- Modify: `ui/productize_helpers.py`

- [ ] Record code quality in reproduce results when implementation bundles are generated.
- [ ] Show code quality issues in the Reproduce UI generated-code section.
- [ ] Show generated product summary and actual run command in Productize result UI.
- [ ] Run focused UI/helper tests.

### Task 4: Prompt and Guideline Upgrade

**Files:**
- Modify: `prompts/prototype_builder_prompt.txt`
- Modify: `guidelines/streamlit_ui_rules.md`

- [ ] Add concrete planning requirements for information architecture, controls, result views, states, and visual restraint.
- [ ] Keep safety constraints intact.

### Task 5: Verification and Publish

**Files:**
- All changed files

- [ ] Run focused tests.
- [ ] Run the broader available test suite if dependencies permit.
- [ ] Inspect `git diff`.
- [ ] Commit and push `codex/product-quality-ui-upgrade`.
