# Sample Input

Use these values when trying PaperPilot in Mock Mode (`LLM_MOCK_MODE=true`) or with a real API key.

## Reproduce Mode

| Field | Example |
|-------|---------|
| Paper PDF | Any ML paper PDF (e.g. a short arXiv preprint) |
| GitHub URL (optional) | `https://github.com/owner/small-demo-repo` |
| Hardware | `Single GPU` |
| GPU model | `RTX 4090` |
| Goal | `run official demo` |
| Paper name | `my_paper_run` (controls `outputs/<paper_name>/`) |

## Productize Mode

| Field | Example |
|-------|---------|
| Paper PDFs | One or two related papers |
| GitHub URL(s) | One shared URL, or one URL per paper (one per line) |
| Target user | `Machine learning learners` |
| Product goal | `Turn the paper technology into an interactive course demo.` |
| Preferred product type | `Auto` |

## Mock vs real mode

- **Mock Mode** (default): parses PDFs and runs the pipeline with fixed LLM placeholders — no API key required.
- **Real mode**: set `LLM_MOCK_MODE=false` and configure `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` in the sidebar or environment.

## OCR for scanned PDFs

If native text extraction yields very little text, PaperPilot attempts Tesseract OCR when `pytesseract` and the Tesseract binary are installed.
