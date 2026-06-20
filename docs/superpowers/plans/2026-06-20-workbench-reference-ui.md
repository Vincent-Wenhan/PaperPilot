# Workbench Reference UI Implementation Plan

**Goal:** Match the approved PaperPilot reference workbench while preserving the collaborator-provided API-backed run, artifact, evaluation, and approval behavior.

**Architecture:** Keep `WorkspaceShell` as the data and action coordinator. Recompose the existing layout components into a fixed desktop workbench with responsive stacking, and use local mock fixtures only when backend data is unavailable.

## Completed Work

- [x] Reconcile the feature branch with the latest collaborator changes.
- [x] Add Vitest and Testing Library with reference-layout regression tests.
- [x] Rebuild the global navigation and top project/run context bar.
- [x] Reshape Workflow into graph and Activity regions with offline fallback data.
- [x] Make Code the default inspector tab and preserve API file loading.
- [x] Keep Logs, Terminal, Results, and Metrics in a persistent bottom console.
- [x] Connect the floating approval panel to existing approve/edit/reject handlers.
- [x] Add desktop, tablet, and mobile responsive geometry.
- [x] Document frontend run and verification commands.
- [x] Verify frontend tests, TypeScript, lint, production build, and Python tests.
- [x] Inspect desktop and mobile browser screenshots for blank canvases and overlap.

## Verification Commands

```bash
cd frontend
npm test
npx tsc --noEmit
npm run lint
npm run build

cd ..
conda run -n paperpilot pytest -q
```

## Integration

Commit the scoped frontend and documentation changes on `codex/product-quality-ui-upgrade`, then push that branch to `origin`.
