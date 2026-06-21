# PaperPilot Examples

This directory contains sample inputs and outputs that illustrate what
PaperPilot produces without running the full pipeline yourself.

## Contents

| Path | Description |
| --- | --- |
| [`sample_input.md`](sample_input.md) | Example PDF and optional GitHub URL inputs |
| [`sample_outputs/reproduction_plan.md`](sample_outputs/reproduction_plan.md) | Sample structured reproduction plan |
| [`sample_outputs/report.md`](sample_outputs/report.md) | Sample course-ready reproduction report |
| [`sample_outputs/product_spec.md`](sample_outputs/product_spec.md) | Sample PRD / MVP product specification |
| [`screenshots/`](screenshots/) | UI screenshots captured after local runs |

## Quick Preview

1. **Reproduce Mode** produces paper summaries, method breakdowns, environment
   checklists, safe command plans, optional generated reproduction code, and a
   report.
2. **Productize Mode** produces capability cards, method composition, product
   proposals, PRD/MVP scope, and a mock-first static web prototype.

Generated product prototypes can be opened directly from their `index.html` or
served with `python -m http.server` inside the generated product directory.

## Suggested Demo Paper Criteria

Choose a paper with extractable text. If using a repository, prefer a small repo
with a clear README, dependency file, and a lightweight `train.py`, `demo.py`,
or `inference.py` entry point. Avoid projects that require large private
datasets, custom CUDA extensions, or unpublished checkpoints.

## Screenshots

After running the FastAPI backend and Next.js workbench locally, capture:

- `screenshots/upload_page.png` - run intake drawer
- `screenshots/agent_progress.png` - workflow graph and activity stream
- `screenshots/report_page.png` - reproduction outputs
- `screenshots/generated_app.png` - static product prototype result

Placeholders are tracked in `screenshots/README.md`.
