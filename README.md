# PaperPilot 2.0

[中文](README_ZH.md)
![CI](https://github.com/Vincent-Wenhan/PaperPilot/actions/workflows/ci.yml/badge.svg)

PaperPilot is a safety-bounded multi-agent workbench for paper reproduction and research-to-product prototyping. Reproduce Mode analyzes papers and optional GitHub repositories, plans safe reproduction steps, and can generate a small runnable reproduction project. Productize Mode extracts research capabilities, builds a PRD/MVP plan, evaluates it, and generates a mock-first static web prototype with a reviewed adapter boundary.

PaperPilot does not claim automatic full paper reproduction, production-ready model integration, or reproduced metrics.

## Current App Surface

The active UI is the Next.js Agent Workbench backed by FastAPI. The old Streamlit host UI has been removed.

```text
frontend/        Next.js workbench
backend/         FastAPI API, WebSocket events, run/action/file/patch services
graphs/          LangGraph reproduce and productize workflows
pipeline/        Backward-compatible pipeline entry points
productize/      Static product scaffold and inspector
tools/           PDF, repository, command, code-quality, and file tools
workspace/runs/  Run-scoped workbench outputs
outputs/         Backward-compatible local pipeline outputs
```

## Features

- Parse text-based PDFs and gather paper evidence.
- Shallow-scan optional public GitHub repositories.
- Build structured research understanding, repository understanding, reproduction plans, and reports.
- Generate bounded reproduction code from an implementation blueprint.
- Gate generated code with deterministic quality checks, blueprint coverage, syntax checks, smoke-test expectations, assertion-bearing tests, and placeholder-name rejection.
- Route risky commands and patch application through reviewable actions.
- Stream workbench events over WebSocket from the backend event service.
- Productize one or multiple papers into capability cards, method composition, PRD, MVP scope, prototype plan, and evaluation.
- Generate product prototypes as static browser bundles: `index.html`, `app.js`, `adapter.js`, `styles.css`, `README.md`, `product_spec.md`, and `outputs/`.

## Install

Python 3.12 is recommended.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip check
python -c "import fitz, langgraph, openai, yaml; print('imports ok')"
```

For the workbench frontend:

```bash
cd frontend
npm ci
```

## Run

Start the FastAPI backend:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Start the Next.js frontend in another terminal:

```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open `http://localhost:3000`.

## LLM Configuration

PaperPilot uses an OpenAI-compatible Chat Completions client. Configure via the workbench settings/API or environment variables:

```bash
set LLM_API_KEY=...
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini
set LLM_MOCK_MODE=false
```

`LLM_MOCK_MODE=true` runs local mock outputs for demos. API keys are not written to repository config files.

## Reproduce Mode

Reproduce Mode follows this high-level graph:

```text
parse paper -> research understanding
            -> repository preparation -> repository understanding
            -> reproduction planning -> optional implementation
            -> code review / revision / sandbox checks
            -> execution diagnosis -> reports
```

Generated reproduction code is written to a separate generated repository and copied into run outputs for browsing. Workbench-created runs write artifacts under:

```text
workspace/runs/<run_id>/outputs/
workspace/runs/<run_id>/outputs/code/
```

Backward-compatible direct pipeline calls still use `outputs/`.

## Productize Mode

Productize Mode generates proposals first, then executes a selected proposal:

```text
papers -> capability cards -> synthesis -> PRD/MVP
      -> prototype plan -> evaluation/revision -> static scaffold
```

Generated product bundles are static web prototypes. They do not require Streamlit or Python dependencies:

```text
generated_product/<product_name>/
  index.html
  app.js
  adapter.js
  styles.css
  README.md
  product_spec.md
  outputs/
```

Run a generated prototype by opening `index.html` directly, or serve the directory:

```bash
cd generated_product/<product_name>
python -m http.server 8000
```

Workbench-created Productize runs write the generated product under:

```text
workspace/runs/<run_id>/generated_product/
```

The generated `adapter.js` defaults to mock mode. Real model integration requires manual review of the source repository inference path before disabling mock mode.

## Verification

```bash
python -m compileall main.py config.py
python -m compileall agents tools pipeline productize schemas runtime graphs backend
python -m pytest tests/ -q
cd frontend && npm test && npm run build
```
