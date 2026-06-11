# Agent Architecture Convergence Implementation Plan

**Status:** Implemented on `feat/agent-architecture-convergence`.

## Problem

The functional upgrade added four high-level Productize agents, but the active
Reproduce pipeline still called the original fragmented agents directly. The
top-level `agents/` package also still exposed legacy Productize, Runner,
Debug, Code, and repository-clone wrappers. This did not satisfy Phase 4 of
`docs/PaperPilot_Functional_Upgrade_Plan.md`.

## Target Architecture

The active system exposes exactly eight high-level reasoning agents:

### Reproduce Mode

1. `ResearchUnderstandingAgent`
2. `RepositoryUnderstandingAgent`
3. `ReproductionPlannerAgent`
4. `ExecutionDiagnosisAgent`

### Productize Mode

1. `ResearchSynthesizerAgent`
2. `ProductPlannerAgent`
3. `PrototypeBuilderAgent`
4. `ProductEvaluatorAgent`

Deterministic modules own repository cloning/scanning, command execution,
artifact writing, product scaffolding, and static inspection.

## Compatibility Strategy

- Preserve the public `run_paperpilot()` and `run_reproduce_pipeline()`
  signatures and legacy result keys used by the UI and Productize Mode.
- Move old agent implementations into `agents/legacy/`.
- Do not export legacy agents from `agents/__init__.py`.
- The new pipeline does not call legacy agents.
- When no repository URL is provided, Reproduce Mode continues with a
  paper-only repository understanding instead of asking Code Agent to invent a
  repository.
- Runner safe/review/sandbox behavior remains in `tools/command_runner.py`.
- UI error diagnosis uses `ExecutionDiagnosisAgent`.

## Structured Artifacts

Add `schemas/reproduction_schema.py` for:

- `PaperUnderstanding`
- `RepositoryUnderstanding`
- `ReproductionPlan`
- `ExecutionDiagnosis`

The pipeline stores these structured artifacts while also rendering existing
Markdown-compatible fields:

- `paper_info`
- `method_info`
- `repo_info`
- `env_plan`
- `experiment_plan`
- `report`
- `run_sh`

## Active Pipeline

1. Parse the paper with the deterministic PDF parser.
2. Run `ResearchUnderstandingAgent`.
3. Optionally clone and scan a GitHub repository with deterministic tools.
4. Run `RepositoryUnderstandingAgent`.
5. Run `ReproductionPlannerAgent`.
6. Run `ExecutionDiagnosisAgent` over planned/not-yet-executed commands.
7. Build `reproduction_plan.md`, `run.sh`, and `report.md` deterministically.

## Tests and Acceptance

- The active pipeline calls only the four high-level Reproduce agents.
- `agents/__init__.py` exports only the eight high-level agents and base
  classes.
- All legacy implementations live under `agents/legacy/`.
- No top-level fragmented-agent files remain.
- Existing UI result keys and Productize reuse remain compatible.
- Full pytest, compileall, mock pipeline smoke, Streamlit headless startup,
  and `git diff --check` pass.
