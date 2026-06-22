# Manifest Driven Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fixed-file assumptions in Productize and Reproduce outputs with manifest-driven generated bundles that can include frontend, backend, adapter, docs, dependencies, and run commands.

**Architecture:** Productize will produce a structured app bundle from generated file specs plus deterministic safety files. Reproduce will keep existing generated implementation files but add a manifest and directory-aware output discovery so consumers no longer depend on only `reproduction_plan.md`, `run.sh`, and `report.md`.

**Tech Stack:** Python 3.12, Pydantic schemas, FastAPI scaffold text generation, existing unittest/pytest tests.

## Global Constraints

- Generated files may only be written below `generated_product/`, `workspace/runs/<run_id>/generated_product/`, or the selected reproduce output directory.
- Real model paths remain mock-first and must not download weights, install packages, train models, or execute analyzed repositories automatically.
- Every generated bundle must include a machine-readable `manifest.json`.
- Tests define behavior before production code changes.

---

### Task 1: Productize Manifest Bundle

**Files:**
- Modify: `schemas/product_schema.py`
- Modify: `agents/prototype_builder_agent.py`
- Modify: `prompts/prototype_builder_prompt.txt`
- Modify: `productize/product_scaffold.py`
- Modify: `productize/product_templates.py`
- Modify: `productize/product_tester.py`
- Test: `tests/test_product_scaffold.py`
- Test: `tests/test_product_pipeline.py`

**Interfaces:**
- Produces: `PrototypeFileSpec`, `PrototypeEndpointSpec`, `PrototypeDependencySpec`, and `PrototypePlan.generated_files`.
- Produces: `scaffold_product(...).files` from actual manifest entries.

**Steps:**
- [ ] Add failing tests that Productize can generate `backend/main.py`, `backend/adapter.py`, `frontend/app.js`, `frontend/index.html`, `requirements.txt`, and `manifest.json`.
- [ ] Run the targeted tests and confirm they fail because files/schema are missing.
- [ ] Extend `PrototypePlan` with optional generated file, endpoint, dependency, and command specs.
- [ ] Change scaffold generation to use `PrototypePlan.generated_files` when present, with deterministic fallback file specs.
- [ ] Update product inspector to validate manifest entries and Python/JS syntax without requiring one fixed static bundle.
- [ ] Run targeted tests, then full relevant product tests.

### Task 2: Reproduce Output Manifest

**Files:**
- Modify: `pipeline/reproduce_pipeline.py`
- Modify: `pipeline/output_builder.py`
- Modify: `pipeline/output_paths.py`
- Modify: `pipeline/hitl_retry.py`
- Test: `tests/test_e2e_pipeline.py`
- Test: `tests/test_improvements.py`
- Test: `tests/test_agent_architecture.py`

**Interfaces:**
- Produces: `outputs/manifest.json` listing generated artifacts, generated code files, commands, and entrypoints.
- Keeps: existing markdown/script outputs for backward compatibility.

**Steps:**
- [ ] Add failing tests that Reproduce writes and refreshes `manifest.json`.
- [ ] Run targeted tests and confirm manifest is missing.
- [ ] Implement `build_reproduce_manifest(result, saved_outputs, output_dir)`.
- [ ] Save manifest from `_save_outputs()` and HITL refresh.
- [ ] Update output path helpers to resolve manifest entries while retaining legacy filenames.
- [ ] Run targeted reproduce tests, then full backend tests if feasible.

### Task 3: Verification And Commit

**Files:**
- No new production files beyond Tasks 1-2.

**Steps:**
- [ ] Run `pytest tests/test_product_scaffold.py tests/test_product_pipeline.py tests/test_e2e_pipeline.py tests/test_improvements.py tests/test_agent_architecture.py -q`.
- [ ] Run `npm run test`, `npm run build`, and `npm run lint` under `frontend/` if frontend contracts are touched.
- [ ] Commit with `feat(productize): generate manifest driven app bundles`.
- [ ] Push when GitHub network is reachable.

