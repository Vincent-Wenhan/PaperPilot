# P2 Improvements — Design Document

> 2026-06-10

## Overview

Five independent enhancement areas for PaperPilot targeting repo analysis depth, PDF robustness, documentation, and project presentation. Each maps to a section of `docs/PaperPilot_Improvement_Plan.md`.

## P2-8: Repo Scanner Structured Evidence

### Current State

`scan_repo()` returns flat file listings (entrypoints, config files, important files) plus raw content of README/requirements/environment/setup. No framework or risk analysis.

### Enhancement

Add `scan_repo_detailed(repo_path)` that returns everything `scan_repo` does plus additional analysis:

**Framework detection:** Scan file contents for import patterns (`import torch`, `from tensorflow`, `import jax`, `from sklearn`, `import pytorch_lightning`, `import keras`). Return `detected_framework: str` (one of: pytorch, tensorflow, jax, sklearn, pytorch_lightning, keras, lightning, or "unknown").

**Config system detection:** Scan for known config libraries in imports (`from hydra`, `import argparse`, `import yaml`, `from omegaconf`).

**Risk signals:** Check for:
- `missing_requirements`: no requirements.txt, environment.yml, setup.py, or pyproject.toml
- `no_readme`: no README file found
- `no_checkpoint_link`: README content lacks "checkpoint", "pretrained", "weights", "model zoo" keywords
- `hardcoded_paths`: .py files contain absolute paths like `/data`, `/home`, `/mnt`
- `large_dataset_required`: README mentions large datasets (imagenet, coco, cityscapes, etc.)
- `cuda_extension`: presence of .cu files or `cpp_extension` / `CUDAExtension` in setup

**Additional entrypoints:** Expand ENTRYPOINT_NAMES to include `run.py`, `inference.py`, `app.py`, `server.py`.

**Output schema:**

```json
{
  "repo_name": "string",
  "detected_framework": "pytorch | tensorflow | jax | sklearn | lightning | unknown",
  "main_language": "python (default)",
  "has_training_code": true,
  "has_inference_code": true,
  "config_systems": ["argparse", "yaml", "hydra"],
  "entrypoints": ["train.py", ...],
  "risk_signals": ["missing_requirements", ...],
  "reproduction_risks": ["No checkpoint link found", ...],
  "notes": ["Detected PyTorch 2.x features", ...]
}
```

### Files Changed

- Modify: `tools/repo_scanner.py` — add `scan_repo_detailed()` and helper functions
- Modify: `tests/test_repo_scanner.py` — add tests for new scanning

## P2-9: PDF Quality and Caption Detection

### Current State

`parse_pdf()` extracts all text, returns it truncated to 50K chars. No quality metrics or structural markup extraction.

### Enhancement

Add `analyze_pdf_quality(pdf_path)` returning:

```python
{
    "total_chars": int,
    "num_pages": int,
    "avg_chars_per_page": float,
    "is_scanned": bool,        # True if avg_chars_per_page < 100
    "warnings": [str],
}
```

Add `extract_pdf_sections(pdf_path)` that returns:

```python
{
    "main_text": str,          # All extracted text (like parse_pdf)
    "figures": [str],          # Paragraphs containing Figure/Fig. references
    "tables": [str],           # Paragraphs containing Table references
    "algorithms": [str],       # Paragraphs containing Algorithm references
    "equations": [str],        # Lines containing inline/math notation
    "warnings": [str],         # Quality warnings
}
```

Caption extraction works by scanning each page's text blocks for lines starting with "Figure", "Fig.", "Table", "Algorithm" and collecting them plus the surrounding text block. This is regex-based, not ML — no new dependencies.

**Scanned PDF guard:** In `parse_pdf()`, if extracted text has < 100 chars per page on average, add a warning to result or raise a more specific `ValueError` suggesting OCR.

### Files Changed

- Modify: `tools/pdf_parser.py` — add `analyze_pdf_quality()`, `extract_pdf_sections()`, scanned PDF guard
- Modify: `tests/test_pdf_parser.py` — add tests

## P2-10: Examples Directory

Create `examples/` directory with:

```
examples/
├── sample_outputs/
│   ├── reproduction_plan.md        # Mock example of a generated reproduction plan
│   ├── report.md                   # Mock example of a generated report
│   └── product_spec.md             # Mock example of a product spec
```

The samples are illustrative markdown files showing what the output looks like for a hypothetical paper (e.g., "A Novel Approach to Image Classification"). They serve as quick references for users who want to understand the output format without running the system.

### Files Created

- Create: `examples/README.md`
- Create: `examples/sample_outputs/reproduction_plan.md`
- Create: `examples/sample_outputs/report.md`
- Create: `examples/sample_outputs/product_spec.md`
- Create: `.gitkeep` in `examples/sample_outputs/` (git tracks the directory)

## P2-11: README Enhancements

### Changes to README.md

1. **CI badge** at top (already referenced in the plan, but the badge won't render until CI runs — still add it):

```
![CI](https://github.com/Vincent-Wenhan/PaperPilot/actions/workflows/ci.yml/badge.svg)
```

2. **Features section** restructured: move the existing bullet list under "Features" to be more scannable and add mock-first emphasis.

3. **Mock-first philosophy section** as a new subsection:

```markdown
## Why Mock-first?

Many research repositories are difficult to run directly because of missing checkpoints,
large datasets, environment conflicts, or undocumented preprocessing steps.

PaperPilot therefore uses a mock-first productization strategy:

1. Understand the paper and optional repository.
2. Identify a feasible product scenario.
3. Generate a clean interface and adapter boundary.
4. Use mock outputs by default.
5. Leave real model integration as a reviewed engineering step.

This makes the generated prototype safe, fast to run, and suitable for course demos
or early product validation.
```

4. **Add example outputs reference** in README pointing to `examples/`.

### Files Changed

- Modify: `README.md`
- Modify: `README_ZH.md` (mirror relevant changes in Chinese)

## Implementation Order

```
1. P2-8: Repo Scanner structured evidence (standalone, no dependencies)
2. P2-9: PDF quality detection (standalone)
3. P2-10: Examples directory (standalone)
4. P2-11: README enhancements (bundles at end)
```

Each is independently testable. Commit after each task.

## Verification

- `pytest tests/test_repo_scanner.py -v` — new scanner tests pass
- `pytest tests/test_pdf_parser.py -v` — new PDF tests pass
- `python -c "import ast; ast.parse(open('tools/repo_scanner.py').read())"` — syntax check
- `python -c "import ast; ast.parse(open('tools/pdf_parser.py').read())"` — syntax check
- Review README renders correctly
- All 51+ existing tests still pass
