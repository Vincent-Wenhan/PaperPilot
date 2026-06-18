# PaperPilot Workbench

Next.js preview surface for the PaperPilot Research Agent IDE.

## Run

```bash
npm install
npm run dev
```

By default the UI falls back to local mock data when the API is unavailable.
When FastAPI is running, the workspace reads snapshot, artifact, and file
content from the backend. To point API-backed components at a different
backend:

```bash
NEXT_PUBLIC_PAPERPILOT_API_BASE=http://localhost:8000 npm run dev
```

## Current Scope

- Three-column agent workspace.
- Static workflow graph for Reproduce Mode.
- Co-planning, event stream, action approval, inspector tabs.
- Code, diff, runner, tool-call, logs, and preview panels.
- API-backed artifact and file browsing with mock fallback.

The existing Streamlit app remains the stable execution UI while the FastAPI
facade and event stream are connected to live pipelines.
