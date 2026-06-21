# Productize Multi-Paper Proposal Selection Design

Date: 2026-06-22

## Goal

Make Workbench Productize mode match the documented product requirement: users can submit multiple paper PDFs, review 2-3 generated product proposals, choose one proposal, and then execute prototype generation for that selected proposal.

## Current State

The core productize pipeline already has partial support:

- `pipeline.productize_pipeline.generate_proposals()` accepts `papers`.
- `schemas.product_schema.ProductProposal` models proposal data.
- `graphs.productize_graph` builds proposals from product opportunities.

The Workbench API and frontend do not expose this flow. `RunCreateRequest` accepts one `pdf_path`, the frontend upload control accepts one PDF, and backend Productize mode calls `run_productize_pipeline()`, which automatically executes the first proposal.

## Design

### API Contract

`RunCreateRequest` gains `pdf_paths: list[str]` while keeping `pdf_path` for backward compatibility. Productize mode resolves the effective papers from `pdf_paths` when present, otherwise from `pdf_path`.

The run result for Productize proposal generation includes:

- `productize_stage: "proposal_review"`
- `productize_proposals: list[dict]`
- `research_synthesis`
- `papers`

The run status becomes `waiting_review` until the user executes a selected proposal.

A new endpoint executes one selected proposal:

`POST /api/runs/{run_id}/productize/proposals/{proposal_index}/execute`

It validates the run, proposal index, and stored proposal context, then calls `execute_proposal()` and stores the final product result.

### Backend Flow

For each selected PDF, Productize mode runs the existing analysis stage with `run_paperpilot(generate_code=False)`. It creates one normalized paper record per PDF and passes all papers into `generate_proposals()`.

The backend caps the exposed proposals to 2-3:

- If the planner returns more than three proposals, keep the top three by list order.
- If it returns one proposal, expose one rather than inventing fake alternatives.
- If no proposal is produced, fail the run with a clear error.

Proposal execution reuses the stored paper list and research synthesis. It writes generated product files into the existing run-scoped generated product directory.

### Frontend Flow

Productize mode uses the same drawer but enables multi-file PDF selection. The upload handler uploads all selected PDFs, stores all returned paths in `pdf_paths`, and keeps `pdf_path` as the first uploaded path for compatibility.

The productize result panel detects `productize_proposals` and renders proposal cards with a select/execute button. Selecting a proposal calls the new API endpoint, refreshes the run, events, graph, actions, files, and result, and then shows the generated product output.

### Testing

Backend tests cover:

- `RunCreateRequest` stores `pdf_paths`.
- Productize analysis runs once per PDF and passes all paper records to `generate_proposals()`.
- Productize proposal generation pauses in `waiting_review`.
- Proposal execution calls `execute_proposal()` with the selected proposal and stored context.

Frontend verification uses the existing Next build/typecheck. The new API client function and UI types must compile cleanly.

## Non-Goals

- No editable proposal form in this change.
- No new upload endpoint; reuse `/api/upload/pdf`.
- No change to Reproduce mode behavior.
- No generated product runtime launch in CI.
