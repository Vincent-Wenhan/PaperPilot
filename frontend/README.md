# PaperPilot Workbench

Next.js preview surface for the PaperPilot Research Agent IDE.

## Run

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:3000` after Next.js reports that it is ready.

By default the UI falls back to local mock data when the API is unavailable.
When FastAPI is running, the workspace reads snapshot, artifact, and file
content from the backend. To point API-backed components at a different
backend:

```bash
NEXT_PUBLIC_PAPERPILOT_API_BASE=http://localhost:8000 npm run dev
```

## Verify

```bash
npm test
npx tsc --noEmit
npm run lint
npm run build
```

## Current Scope

- Reference-aligned navigation, project context, workflow, inspector, and console layout.
- API-backed workflow graph with a representative offline demo fallback.
- Co-planning, event stream, floating action approval, and workspace tabs.
- Code, diff, runner, tool-call, logs, results, and metrics panels.
- API-backed artifact and file browsing with mock fallback.

The Next.js workbench is the active execution UI. FastAPI provides live runs,
artifacts, files, event streaming, action approval, syntax checks, and patch
application through reviewed actions.
