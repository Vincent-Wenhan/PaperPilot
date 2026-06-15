# PaperPilot Examples

This directory contains sample inputs and outputs that illustrate what PaperPilot produces without running the full pipeline yourself.

## Contents

| Path | Description |
|------|-------------|
| [`sample_input.md`](sample_input.md) | Example PDF + optional GitHub URL inputs for Reproduce and Productize modes |
| [`sample_outputs/reproduction_plan.md`](sample_outputs/reproduction_plan.md) | Sample structured reproduction plan |
| [`sample_outputs/report.md`](sample_outputs/report.md) | Sample course-ready reproduction report |
| [`sample_outputs/product_spec.md`](sample_outputs/product_spec.md) | Sample PRD / MVP product specification |
| [`screenshots/`](screenshots/) | UI screenshots (add PNGs after local runs) |

## Quick preview

1. **Reproduce Mode** — upload a paper PDF, optionally link a GitHub repo, and receive:
   - parsed paper summary and method breakdown
   - environment checklist and experiment plan
   - safe `run.sh` script stub
   - `report.md` for submission

2. **Productize Mode** — upload one or more papers and receive:
   - capability cards and composition plan
   - multiple product proposals (JTBD / PRD / MVP)
   - mock-first Streamlit prototype under `generated_product/`

## Suggested demo paper criteria

Choose a small repo with a clear README, `requirements.txt`, and a `train.py` / `demo.py` entry point. Avoid projects that need large private datasets or custom CUDA extensions.

## Screenshots

After running `streamlit run app.py` locally, capture:

- `screenshots/upload_page.png` — main input form
- `screenshots/agent_progress.png` — agent progress during analysis
- `screenshots/report_page.png` — reproduction outputs
- `screenshots/generated_app.png` — productize prototype result

Placeholders are tracked in `screenshots/README.md`.
