# Productize Multi-Paper Proposal Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose Productize multi-paper input and human proposal selection through the Workbench API and frontend.

**Architecture:** Keep the existing productize graph and schema as the source of truth. Add Workbench API orchestration around `generate_proposals()` and `execute_proposal()`, store proposal-review state in the existing run result store, and let the frontend render proposals from run result data.

**Tech Stack:** Python 3, FastAPI, Pydantic, pytest, Next.js 14, TypeScript, React.

---

## File Structure

- Modify `backend/schemas.py`: add `pdf_paths` to `RunCreateRequest`.
- Modify `backend/services/run_service.py`: resolve multi-PDF inputs, generate proposals without auto-execution, store proposal review result, execute selected proposal.
- Modify `backend/routers/runs.py`: add selected proposal execution endpoint.
- Modify `frontend/lib/api.ts`: add `pdf_paths` request field and proposal execution client.
- Modify `frontend/components/layout/project-sidebar.tsx`: add `pdf_paths` to form state type.
- Modify `frontend/components/run/run-intake-drawer.tsx`: enable multi-PDF upload in Productize mode and show selected files.
- Modify `frontend/components/workspace-shell.tsx`: upload multiple files, submit `pdf_paths`, render and execute proposals.
- Modify `tests/test_workbench_backend_services.py`: add backend contract tests.
- Keep existing `tests/test_product_pipeline.py` coverage for core graph behavior.

### Task 1: Backend Request Contract

**Files:**
- Modify: `backend/schemas.py`
- Test: `tests/test_workbench_backend_services.py`

- [ ] **Step 1: Write the failing test**

Add a test that constructs `RunCreateRequest(mode="productize", pdf_paths=["a.pdf", "b.pdf"])` and asserts both paths are preserved and `pdf_path` remains optional.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_workbench_backend_services.py::WorkbenchBackendServiceTests::test_productize_request_accepts_multiple_pdf_paths -v`

Expected: FAIL because `pdf_paths` is not available on the model.

- [ ] **Step 3: Implement minimal schema change**

Add `pdf_paths: list[str] = Field(default_factory=list)` to `RunCreateRequest`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_workbench_backend_services.py::WorkbenchBackendServiceTests::test_productize_request_accepts_multiple_pdf_paths -v`

Expected: PASS.

### Task 2: Backend Proposal Review Flow

**Files:**
- Modify: `backend/services/run_service.py`
- Test: `tests/test_workbench_backend_services.py`

- [ ] **Step 1: Write failing tests**

Add tests that patch `main.run_paperpilot` and `pipeline.productize_pipeline.generate_proposals`, then call `_execute_productize()` with two PDF paths. Assert analysis runs twice, `generate_proposals()` receives two paper records, the result has `productize_stage == "proposal_review"`, and proposals are capped at three.

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_workbench_backend_services.py::WorkbenchBackendServiceTests::test_productize_generates_reviewable_proposals_for_multiple_papers -v`

Expected: FAIL because `_execute_productize()` only handles one PDF and auto-executes the first proposal.

- [ ] **Step 3: Implement proposal generation**

Add helpers in `InMemoryRunService`:

- `_effective_pdf_paths(request) -> list[Path]`
- `_analyze_productize_paper(run_id, pdf_path, request, client, progress, index) -> dict[str, Any]`
- `_proposal_review_result(proposals, proposal_context) -> dict[str, Any]`

Change `_execute_pipeline()` and `_execute_productize()` so Productize mode validates all effective PDF paths and calls `generate_proposals()` instead of `run_productize_pipeline()`.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_workbench_backend_services.py::WorkbenchBackendServiceTests::test_productize_generates_reviewable_proposals_for_multiple_papers -v`

Expected: PASS.

### Task 3: Backend Selected Proposal Execution Endpoint

**Files:**
- Modify: `backend/services/run_service.py`
- Modify: `backend/routers/runs.py`
- Test: `tests/test_workbench_backend_services.py`

- [ ] **Step 1: Write failing test**

Add a test that stores a proposal-review result, patches `pipeline.productize_pipeline.execute_proposal`, calls `service.execute_productize_proposal(run_id, 1)`, and asserts it executes the second proposal with stored papers and research synthesis.

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_workbench_backend_services.py::WorkbenchBackendServiceTests::test_productize_executes_selected_proposal_from_review_state -v`

Expected: FAIL because no execution method exists.

- [ ] **Step 3: Implement service and route**

Add `execute_productize_proposal(run_id, proposal_index)` to `InMemoryRunService` and route `POST /api/runs/{run_id}/productize/proposals/{proposal_index}/execute`.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_workbench_backend_services.py::WorkbenchBackendServiceTests::test_productize_executes_selected_proposal_from_review_state -v`

Expected: PASS.

### Task 4: Frontend Multi-PDF Upload and Proposal Execution

**Files:**
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/components/layout/project-sidebar.tsx`
- Modify: `frontend/components/run/run-intake-drawer.tsx`
- Modify: `frontend/components/workspace-shell.tsx`

- [ ] **Step 1: Update TypeScript contracts**

Add `pdf_paths?: string[]` to `ApiRunCreateRequest`, add proposal result types, and add `executeProductizeProposal(runId, proposalIndex)`.

- [ ] **Step 2: Update form state and uploader**

Add `pdf_paths: string[]` to `RunFormState`, set `multiple={runForm.mode === "productize"}`, upload every selected PDF, and show the uploaded file names.

- [ ] **Step 3: Update submit validation**

For Productize mode, allow submit when `pdf_paths.length > 0`; for Reproduce, keep requiring `pdf_path`.

- [ ] **Step 4: Render proposal cards**

In the productize workbench panel, detect `runResult.productize_proposals` and render product name, target user, JTBD, core features, risks, and an execute button.

- [ ] **Step 5: Execute selected proposal**

Button calls `executeProductizeProposal`, refreshes current run state, and updates notice/timeline.

- [ ] **Step 6: Build frontend**

Run: `npm run build` in `frontend`.

Expected: PASS.

### Task 5: Verification, Commit, Push

**Files:**
- All changed files.

- [ ] **Step 1: Run backend syntax check**

Run: `python -m compileall main.py config.py` and `python -m compileall agents tools pipeline productize schemas runtime graphs backend`.

Expected: both commands exit 0.

- [ ] **Step 2: Run backend tests**

Run: `pytest tests/ -v --tb=long`.

Expected: all tests pass.

- [ ] **Step 3: Run frontend build**

Run: `npm run build` in `frontend`.

Expected: build succeeds.

- [ ] **Step 4: Review git diff**

Run: `git diff --stat` and `git diff`.

Expected: only feature, tests, and docs changes are present.

- [ ] **Step 5: Commit and push**

Run: `git add ...`, `git commit -m "feat(productize): add multi-paper proposal selection"`, and `git push`.

Expected: commit succeeds and push updates the current branch.
