# UI and Interaction Upgrade Implementation

## Scope

This implementation starts the upgrade path described in
`PaperPilot_UI_and_Interaction_Upgrade_Plan.md` without replacing the current
Streamlit application.

Implemented scope:

- Add `frontend/` with a Next.js TypeScript workbench shell.
- Add a three-column Research Agent IDE layout.
- Add static workflow visualization, event timeline, co-planning, approval,
  inspector tabs, code view, diff view, runner review, and tool-call trace.
- Add `backend/` with a FastAPI facade for runs, events, artifacts, files, and
- Add `backend/` with a FastAPI facade for runs, events, artifacts, files,
  patch proposals, static checks, reviewed commands, and action approval.
- Keep existing Streamlit entry point and agent pipelines unchanged.

## Architecture

```text
app.py                    # Legacy Streamlit UI remains available
frontend/                 # Next.js Agent Workbench shell
backend/                  # FastAPI API facade
  routers/
  services/
  schemas.py
agents/ graphs/ pipeline/ # Existing PaperPilot core
```

## Current API Facade

The first backend pass exposes stable contracts before live pipeline execution
is wired in:

- `GET /api/health`
- `GET /api/workbench/mock`
- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events`
- `WS /ws/runs/{run_id}`
- `GET /api/artifacts/{run_id}`
- `GET /api/artifacts/{run_id}/{artifact_id}`
- `GET /api/files/{run_id}`
- `GET /api/files/{run_id}/content?path=...`
- `POST /api/patches/{run_id}/propose`
- `GET /api/patches/{run_id}/{patch_id}`
- `POST /api/patches/{run_id}/apply/{patch_id}`
- `POST /api/checks/{run_id}/syntax`
- `POST /api/commands/{run_id}/review`
- `POST /api/commands/{run_id}/run`
- `GET /api/commands/{run_id}/result`
- `POST /api/actions/{action_id}/approve`
- `POST /api/actions/{action_id}/reject`
- `POST /api/actions/{action_id}/edit`

## Safety

- The API facade is read-only for files and artifacts.
- File browsing is restricted to `workspace/`, `outputs/`,
  `generated_product/`, and `examples/sample_outputs/`.
- Patch apply is restricted to `workspace/` and `generated_product/`.
- Syntax checks compile Python files without launching generated apps.
- Command execution delegates to the existing allowlist and risk routing in
  `tools.command_runner`.
- Approval endpoints update in-memory action state only; they do not execute
  commands.
- Existing Runner safety policy remains unchanged.

## Next Integration Steps

1. Connect `POST /api/runs` to upload/session storage.
2. Wrap `run_paperpilot()`, `generate_proposals()`, and `execute_proposal()`.
3. Convert pipeline progress callbacks and graph traces into persisted events.
4. Drive workflow node status from event stream.
5. Persist patch history and command results beyond process memory.
6. Gate patch apply and reviewed command execution through durable approvals.
