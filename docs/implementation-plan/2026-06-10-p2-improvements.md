# P2 Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P2 improvements from PaperPilot_Improvement_Plan.md: repo scanner structured evidence, PDF quality/caption detection, examples directory, README enhancements.

**Architecture:** Four independent tasks touching `tools/repo_scanner.py`, `tools/pdf_parser.py`, new `examples/` directory, and README files. Each is testable independently.

**Tech Stack:** Python, PyMuPDF (fitz), pytest

---

### Task 1: Add `scan_repo_detailed()` with structured evidence

**Files:**
- Modify: `tools/repo_scanner.py`
- Test: `tests/test_repo_scanner.py`

- [ ] **Step 1: Add framework/keyword detection helpers to repo_scanner.py**

Add these constants and helper functions after the existing constants in `tools/repo_scanner.py`:

```python
FRAMEWORK_PATTERNS: dict[str, list[str]] = {
    "pytorch": ["import torch", "from torch", "import torchvision", "from torchvision"],
    "tensorflow": ["import tensorflow", "from tensorflow", "import tf", "from tf"],
    "jax": ["import jax", "from jax", "import flax", "from flax"],
    "sklearn": ["import sklearn", "from sklearn", "from sklearn"],
    "lightning": ["import lightning", "from lightning", "import pytorch_lightning", "from pytorch_lightning"],
    "keras": ["import keras", "from keras", "import tf.keras"],
}

CONFIG_PATTERNS: dict[str, list[str]] = {
    "hydra": ["from hydra", "import hydra", "@hydra"],
    "argparse": ["import argparse", "from argparse", "argparse"],
    "yaml": ["import yaml", "from yaml", "import omegaconf", "from omegaconf"],
    "json": ["import json", "from json"],
    "toml": ["import toml", "from toml", "import tomllib", "from tomllib"],
    "click": ["import click", "from click", "@click"],
}

RISK_DATASET_KEYWORDS = ["imagenet", "coco", "cityscapes", "lsun", "places365",
                         "kinetics", "audioset", "librispeech", "squad", "glue"]
```

Then add:

```python
def _detect_framework(file_texts: list[str]) -> str:
    """Scan file contents to detect the primary ML framework."""
    combined = "\n".join(file_texts).lower()
    # Weight by specificity — check more specific frameworks first
    for framework, patterns in FRAMEWORK_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in combined:
                return framework
    return "unknown"


def _detect_config_systems(file_texts: list[str]) -> list[str]:
    """Detect configuration libraries used in the repo."""
    combined = "\n".join(file_texts)
    detected: list[str] = []
    for system, patterns in CONFIG_PATTERNS.items():
        for pattern in patterns:
            if pattern in combined:
                detected.append(system)
                break
    return detected


def _detect_risk_signals(
    repo_path: Path,
    has_requirements: bool,
    has_readme: bool,
    readme_content: str,
) -> list[dict[str, str]]:
    """Identify potential reproduction risks."""
    risks: list[dict[str, str]] = []

    if not has_requirements:
        risks.append({"signal": "missing_requirements", "detail": "No requirements.txt, environment.yml, setup.py, or pyproject.toml found"})
    if not has_readme:
        risks.append({"signal": "no_readme", "detail": "No README file found"})

    if has_readme and readme_content:
        readme_lower = readme_content.lower()
        ckpt_keywords = ["checkpoint", "pretrained", "pretrain", "weights", "model zoo", "modelzoo", "download"]
        if not any(kw in readme_lower for kw in ckpt_keywords):
            risks.append({"signal": "no_checkpoint_link", "detail": "README does not mention checkpoints, pretrained weights, or model zoo"})

        if any(ds in readme_lower for ds in RISK_DATASET_KEYWORDS):
            risks.append({"signal": "large_dataset_required", "detail": "README mentions a large-scale dataset that may be difficult to obtain"})

    py_files = list(repo_path.rglob("*.py"))
    for py_file in py_files:
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(p in content for p in ["/data/", "/home/", "/mnt/", "C:\\Users", "/scratch/"]):
            risks.append({"signal": "hardcoded_paths", "detail": f"Hardcoded absolute paths detected in {py_file.relative_to(repo_path)}"})
            break

    cu_files = list(repo_path.rglob("*.cu")) + list(repo_path.rglob("*.cuh"))
    if cu_files:
        risks.append({"signal": "cuda_extension", "detail": f"CUDA source files detected ({len(cu_files)} files); may require custom compilation"})

    return risks
```

- [ ] **Step 2: Expand ENTRYPOINT_NAMES and add inference detection**

Change `ENTRYPOINT_NAMES` in `tools/repo_scanner.py`:

Replace:
```python
ENTRYPOINT_NAMES = {"train.py", "main.py", "eval.py", "test.py", "demo.py"}
```
With:
```python
ENTRYPOINT_NAMES = {"train.py", "main.py", "eval.py", "test.py", "demo.py", "run.py", "inference.py", "app.py", "server.py"}
```

Add at the end of the file:

```python
def _has_training_code(entrypoints: list[str]) -> bool:
    return any("train" in ep for ep in entrypoints)


def _has_inference_code(entrypoints: list[str]) -> bool:
    return any(kw in " ".join(entrypoints) for kw in ["infer", "eval", "test", "demo", "app", "predict"])
```

- [ ] **Step 3: Add `scan_repo_detailed()` function**

Add at the end of `tools/repo_scanner.py`:

```python
def scan_repo_detailed(
    repo_path: str | Path,
    max_file_chars: int = 12_000,
) -> dict[str, Any]:
    """Scan repo with structured evidence: framework, config, risks."""
    scan_result = scan_repo(repo_path, max_file_chars)
    root = Path(repo_path).expanduser().resolve()

    # Collect all .py file texts for scanning
    py_texts: list[str] = []
    py_files = list(root.rglob("*.py"))
    rel_parts = root.parts
    for py_file in py_files:
        try:
            if any(part in SKIPPED_DIRECTORIES for part in py_file.relative_to(root).parts):
                continue
            py_texts.append(py_file.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue

    framework = _detect_framework(py_texts)
    entrypoints = [ep for ep in scan_result.get("possible_entrypoints", [])]
    has_readme = bool(scan_result.get("readme_content", ""))
    has_reqs = bool(scan_result.get("requirements_content", ""))
    has_env = bool(scan_result.get("environment_content", ""))
    has_setup = bool(scan_result.get("setup_content", ""))
    has_any_requirements = has_reqs or has_env or has_setup

    risks = _detect_risk_signals(root, has_any_requirements, has_readme, scan_result.get("readme_content", ""))
    config_systems = _detect_config_systems(py_texts)

    repo_name = root.name

    return {
        **scan_result,
        "repo_name": repo_name,
        "detected_framework": framework,
        "main_language": "python",
        "has_training_code": _has_training_code(entrypoints),
        "has_inference_code": _has_inference_code(entrypoints),
        "config_systems": config_systems,
        "risk_signals": [r["signal"] for r in risks],
        "reproduction_risks": [r["detail"] for r in risks],
        "notes": _generate_notes(framework, config_systems, entrypoints, risks),
    }


def _generate_notes(
    framework: str,
    config_systems: list[str],
    entrypoints: list[str],
    risks: list[dict[str, str]],
) -> list[str]:
    notes: list[str] = []
    if framework != "unknown":
        notes.append(f"Detected {framework} framework")
    for cs in config_systems:
        notes.append(f"Detected {cs} configuration system")
    if entrypoints:
        notes.append(f"Found {len(entrypoints)} entrypoint(s): {', '.join(entrypoints[:5])}")
    if not risks:
        notes.append("No significant reproduction risks detected")
    return notes
```

- [ ] **Step 4: Write tests for scan_repo_detailed**

Add to `tests/test_repo_scanner.py`:

```python
class TestRepoScannerDetailed(unittest.TestCase):
    """Test structured evidence scanning."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "train.py").write_text("import torch\nimport argparse\ndef main(): pass")
        (self.root / "inference.py").write_text("from torch import nn\ndef predict(): pass")
        (self.root / "README.md").write_text("# Repo\nUses ImageNet dataset")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_detects_pytorch_framework(self) -> None:
        result = scan_repo_detailed(str(self.root))
        self.assertEqual(result["detected_framework"], "pytorch")

    def test_detects_argparse_config(self) -> None:
        result = scan_repo_detailed(str(self.root))
        self.assertIn("argparse", result["config_systems"])

    def test_detects_training_and_inference_code(self) -> None:
        result = scan_repo_detailed(str(self.root))
        self.assertTrue(result["has_training_code"])
        self.assertTrue(result["has_inference_code"])

    def test_detects_risk_signals(self) -> None:
        os.makedirs(self.root / "cuda", exist_ok=True)
        (self.root / "cuda" / "custom_kernel.cu").write_text("__global__ void kernel() {}")
        result = scan_repo_detailed(str(self.root))
        risk_signals = result["risk_signals"]
        self.assertIn("cuda_extension", risk_signals)
        self.assertIn("no_checkpoint_link", risk_signals)

    def test_repo_name_from_path(self) -> None:
        result = scan_repo_detailed(str(self.root))
        self.assertEqual(result["repo_name"], self.root.name)

    def test_detects_unknown_framework(self) -> None:
        empty_dir = tempfile.TemporaryDirectory()
        empty_path = Path(empty_dir.name)
        (empty_path / "main.py").write_text("print('hello')")
        result = scan_repo_detailed(str(empty_path))
        self.assertEqual(result["detected_framework"], "unknown")
        empty_dir.cleanup()
```

- [ ] **Step 5: Add import for os in test file**

Add `import os` at the top of `tests/test_repo_scanner.py` alongside existing imports:

```python
import os
```

- [ ] **Step 6: Run scanner tests**

Run: `pytest tests/test_repo_scanner.py -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add tools/repo_scanner.py tests/test_repo_scanner.py
git commit -m "feat(scanner): add scan_repo_detailed with framework, config, and risk detection"
```


### Task 2: Add PDF quality check and caption extraction

**Files:**
- Modify: `tools/pdf_parser.py`
- Test: `tests/test_pdf_parser.py`

- [ ] **Step 1: Add analyze_pdf_quality() to pdf_parser.py**

Add at the end of `tools/pdf_parser.py`:

```python
def analyze_pdf_quality(pdf_path: str | Path) -> dict[str, Any]:
    """Analyze PDF text quality: page count, char density, scanned detection."""
    path = Path(pdf_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Missing PyMuPDF dependency.") from exc

    with fitz.open(path) as document:
        if document.needs_pass:
            raise ValueError("PDF is encrypted.")
        num_pages = len(document)
        page_texts: list[str] = []
        for page in document:
            page_texts.append(page.get_text("text"))

    total_chars = sum(len(t) for t in page_texts)
    avg_chars = total_chars / max(num_pages, 1)
    is_scanned = avg_chars < 100

    pdf_path_str = str(path)
    ext = path.suffix.lower()
    filename = path.name

    return {
        "pdf_path": pdf_path_str,
        "filename": filename,
        "total_chars": total_chars,
        "num_pages": num_pages,
        "avg_chars_per_page": round(avg_chars, 1),
        "is_scanned": is_scanned,
        "file_extension": ext,
        "warnings": ["Very low text density; may be a scanned document. Consider OCR."] if is_scanned else [],
    }
```

- [ ] **Step 2: Add extract_pdf_sections() to pdf_parser.py**

Add at the end of `tools/pdf_parser.py`:

```python
SECTION_KEYWORDS = {
    "figures": (r"(?i)\b(figure|fig\.)\s*\d+", 5),
    "tables": (r"(?i)\btable\s*\d+", 4),
    "algorithms": (r"(?i)\balgorithm\s*\d+", 4),
    "equations": (r"(?i)\beq(uation)?\.?\s*\(?\d*\)?", 3),
}


def extract_pdf_sections(
    pdf_path: str | Path,
    max_chars: int = 50_000,
) -> dict[str, Any]:
    """Extract text from PDF with section-specific caption blocks.

    Returns main text plus lists of paragraphs matching figure, table,
    algorithm, or equation references.
    """
    path = Path(pdf_path).expanduser()
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Missing PyMuPDF dependency.") from exc

    with fitz.open(path) as document:
        if document.needs_pass:
            raise ValueError("PDF is encrypted.")
        all_text = ""
        sections: dict[str, list[str]] = {"figures": [], "tables": [], "algorithms": [], "equations": []}
        warnings: list[str] = []

        for page_num, page in enumerate(document, 1):
            blocks = page.get_text("blocks")
            for block in blocks:
                block_text = block[4].strip() if len(block) > 4 else ""
                if not block_text:
                    continue
                all_text += block_text + "\n"

                for section_name, (pattern, _) in SECTION_KEYWORDS.items():
                    import re
                    if re.search(pattern, block_text):
                        # Include surrounding context: prepend truncated block
                        snippet = block_text[:500]
                        sections[section_name].append(f"[Page {page_num}] {snippet}")

        total_chars = len(all_text)
        num_pages = len(document)
        avg_chars = total_chars / max(num_pages, 1)
        if avg_chars < 100:
            warnings.append("Very low text density; may be a scanned document. Consider OCR.")

        cleaned = all_text.strip()[:max_chars]
        return {
            "main_text": cleaned if cleaned else "",
            **{k: v[:20] for k, v in sections.items()},  # cap at 20 per section
            "warnings": warnings,
        }
```

Note: Move the `import re` to the top of the file. Edit the file so `re` is imported at module level.

- [ ] **Step 3: Add `import re` to pdf_parser.py imports**

```python
import re
from pathlib import Path
```

- [ ] **Step 4: Add tests for PDF quality and extraction**

Add to `tests/test_pdf_parser.py`:

```python
class TestPdfQuality(unittest.TestCase):
    """Test PDF quality analysis and section extraction."""

    def test_analyze_raises_on_nonexistent_file(self) -> None:
        from tools.pdf_parser import analyze_pdf_quality
        with self.assertRaises((FileNotFoundError, OSError)):
            analyze_pdf_quality("/nonexistent/paper.pdf")

    def test_extract_raises_on_nonexistent_file(self) -> None:
        from tools.pdf_parser import extract_pdf_sections
        with self.assertRaises((FileNotFoundError, OSError)):
            extract_pdf_sections("/nonexistent/paper.pdf")

    def test_analyze_invalid_extension(self) -> None:
        from tools.pdf_parser import analyze_pdf_quality
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        f.write(b"not a pdf")
        f.close()
        with self.assertRaises(RuntimeError):
            analyze_pdf_quality(f.name)
```

- [ ] **Step 5: Run PDF parser tests**

Run: `pytest tests/test_pdf_parser.py -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add tools/pdf_parser.py tests/test_pdf_parser.py
git commit -m "feat(pdf): add analyze_pdf_quality and extract_pdf_sections with scanned PDF detection"
```


### Task 3: Create examples/ directory

**Files:**
- Create: `examples/sample_outputs/reproduction_plan.md`
- Create: `examples/sample_outputs/report.md`
- Create: `examples/sample_outputs/product_spec.md`
- Create: `examples/sample_outputs/.gitkeep`

- [ ] **Step 1: Create reproduction plan sample**

Create `examples/sample_outputs/reproduction_plan.md`:

```markdown
# Reproduction Plan: A Novel Approach to Image Classification

> This is a sample output illustrating PaperPilot's reproduction plan format.

## Paper Summary

- **Title:** A Novel Approach to Image Classification
- **Task:** Image classification on CIFAR-10
- **Contributions:** Novel attention mechanism, efficient training strategy
- **Method Summary:** Proposes a hybrid CNN-Transformer architecture with a lightweight attention module.

## Method Breakdown

| Module | Description |
|--------|-------------|
| Backbone | ResNet-50 feature extractor |
| Attention | Lightweight cross-attention module |
| Classifier | Linear projection head |

## Repository Analysis

| Field | Value |
|-------|-------|
| Framework | PyTorch |
| Entrypoints | train.py, eval.py, demo.py |
| Config | YAML-based (configs/default.yaml) |
| Risks | No pretrained weights reference found |

## Environment

- Python 3.12
- PyTorch >= 2.0
- torchvision >= 0.15
- CUDA 11.8

## Experiment Roadmap

### Level 0: Environment Setup
- [ ] Create conda environment
- [ ] Install dependencies

### Level 1: Quick Demo
- [ ] Run `python demo.py --help`
- [ ] Run `python demo.py --mock`

### Level 2: Minimal Training
- [ ] Train for 10 epochs: `python train.py --epochs 10`

### Level 3: Full Reproduction
- [ ] Train with default settings: `python train.py`
- [ ] Evaluate: `python eval.py --checkpoint checkpoints/best.pt`

### Level 4: Ablation Studies
- [ ] Run without attention module
- [ ] Compare with baseline ResNet

## Risks

- No pretrained checkpoint link in repository
- Training requires GPU with 8GB+ VRAM
```

- [ ] **Step 2: Create report sample**

Create `examples/sample_outputs/report.md`:

```markdown
# Reproduction Report: A Novel Approach to Image Classification

## Status Summary

- **Paper understood:** Yes
- **Repository analyzed:** Yes (PyTorch, 12 files)
- **Environment plan:** Generated
- **Experiment plan:** Level 0-4 roadmaps ready
- **Commands run:** 3 (all safe)

## Execution Results

| Command | Status | Output |
|---------|--------|--------|
| python --version | Passed | Python 3.12.3 |
| python train.py --help | Passed | Training arguments displayed |
| python demo.py --help | Passed | Demo arguments displayed |

## Key Findings

1. Paper proposes a hybrid CNN-Transformer architecture
2. Training is on CIFAR-10 (small dataset, quick to iterate)
3. No external dependencies beyond PyTorch ecosystem
4. Single GPU training is feasible within course project timeline

## Recommendations

1. Start with mock demo to verify the pipeline
2. Train for 10 epochs to validate loss curve
3. Use pre-trained ResNet backbone if available
4. Consider reducing image size for faster training
```

- [ ] **Step 3: Create product spec sample**

Create `examples/sample_outputs/product_spec.md`:

```markdown
# Product Specification: Image Classifier Web App

## Product Overview

An interactive web application that allows users to upload images and receive
real-time classification results with confidence scores, powered by the paper's
trained model.

## Target User

Students and educators who want to experiment with image classification without
writing code.

## Core Value

One-click image classification with visual confidence breakdown.

## Technical Feasibility

| Dimension | Score (1-5) |
|-----------|-------------|
| Technical Feasibility | 4 |
| Demo Feasibility | 5 |
| Model Availability | 3 |
| Data Requirement | 5 (no new data needed) |
| User Value | 4 |

## MVP Features

1. Image upload (PNG, JPG)
2. Run inference using pre-trained model
3. Display top-5 predictions with confidence bars
4. Show inference time

## Architecture

```text
User uploads image → Preprocessing → Model inference → Display results
                         ↓                              ↑
                    torchvision                   Streamlit UI
                    transforms
```

## Mock-First Strategy

The generated prototype defaults to mock mode, returning plausible
classification results without requiring the actual trained model.
Switch to real model by setting `adapter.mock_mode = False`.
```

- [ ] **Step 4: Create examples .gitkeep**

Create empty `examples/sample_outputs/.gitkeep`.

- [ ] **Step 5: Commit**

```bash
git add examples/
git commit -m "feat(examples): add sample outputs for reproduction plan, report, and product spec"
```


### Task 4: Enhance README with CI badge, mock-first philosophy, and features section

**Files:**
- Modify: `README.md`
- Modify: `README_ZH.md`

- [ ] **Step 1: Add CI badge after title in README.md**

In `README.md`, insert after the title line and the existing badge:

Replace the line:
```markdown
[![GitHub](https://img.shields.io/badge/GitHub-Vincent--Wenhan/PaperPilot-181717?logo=github)](https://github.com/Vincent-Wenhan/PaperPilot) · [中文版](README_ZH.md)
```

With:
```markdown
[![GitHub](https://img.shields.io/badge/GitHub-Vincent--Wenhan/PaperPilot-181717?logo=github)](https://github.com/Vincent-Wenhan/PaperPilot) · [中文版](README_ZH.md)
![CI](https://github.com/Vincent-Wenhan/PaperPilot/actions/workflows/ci.yml/badge.svg)
```

- [ ] **Step 2: Add Features section header**

In `README.md`, replace the "## Features" bullet list header with restructured format. Keep the existing bullet content but add a prefix description and reference examples:

Find the line `## Features` and the bullet list below it. Replace the section:

```markdown
## Features

- Upload and parse paper PDFs
- Optionally validate and shallow-clone public GitHub repositories
- Generate a minimal reproduction codebase with Code Agent when no repository URL is available
- Scan README, dependency files, configurations, and candidate entry points
- Generate paper summaries and engineering-oriented method breakdowns
- Plan environments based on CPU, single-GPU, or multi-GPU
- Generate hierarchical experiment roadmaps, checklists, and safe `run.sh`
- Run version checks and `--help` on lightweight candidate commands
- Automatically analyze Runner failures; also supports manual log pasting for debugging
- Generate and download reproduction plans, scripts, and course-project reports
- Recommend three product ideas and score a feasible MVP
- Generate product specifications, adapter plans, and frontend plans
- Select image, text, video, or generic file-analysis templates
- Generate an isolated Streamlit prototype under `generated_product/`
- Inspect generated files, Python syntax, mock mode, and run instructions
- Full demo via mock mode without any API key
```

With:

```markdown
## Features

PaperPilot combines paper understanding, repository analysis, reproduction planning, and product prototyping in a single workflow. See [`examples/`](examples/) for sample outputs.

### Reproduce Mode

- Upload and parse paper PDFs
- Optionally validate and shallow-clone public GitHub repositories
- Generate a minimal reproduction codebase with Code Agent when no repository URL is available
- Scan README, dependency files, configurations, and candidate entry points
- Generate paper summaries and engineering-oriented method breakdowns
- Plan environments based on CPU, single-GPU, or multi-GPU
- Generate hierarchical experiment roadmaps, checklists, and safe `run.sh`
- Run version checks and `--help` on lightweight candidate commands
- Automatically analyze Runner failures; also supports manual log pasting for debugging
- Generate and download reproduction plans, scripts, and course-project reports

### Productize Mode

- Recommend three product ideas and score a feasible MVP
- Generate product specifications, adapter plans, and frontend plans
- Select image, text, video, or generic file-analysis templates
- Generate an isolated Streamlit prototype under `generated_product/`
- Inspect generated files, Python syntax, mock mode, and run instructions

### Mock Mode

- Full demo via mock mode without any API key
- Mock-first by default — generated prototypes use safe mock outputs
```

- [ ] **Step 3: Add "Why Mock-first?" section in README.md**

Add a new section between "## Project Structure" and "## Installation". Insert after the project structure section:

```markdown
## Why Mock-first?

Many research repositories are difficult to run directly because of missing checkpoints,
large datasets, environment conflicts, or undocumented preprocessing steps.

PaperPilot therefore uses a mock-first productization strategy:

1. **Understand** the paper and optional repository.
2. **Identify** a feasible product scenario.
3. **Generate** a clean interface and adapter boundary.
4. **Mock** by default — prototypes work without the actual model.
5. **Integrate** later — real model integration is a reviewed engineering step.

This makes the generated prototype safe, fast to run, and suitable for course demos
or early product validation.
```

- [ ] **Step 4: Mirror CI badge, features section, and mock-first section in README_ZH.md**

Apply equivalent changes to `README_ZH.md`:

1. Add CI badge after the GitHub link (same badge URL)
2. Restructure Features section into sub-sections (Reproduce Mode, Productize Mode, Mock Mode)
3. Add "Why Mock-first?" section between project structure and installation

For the Chinese version "Why Mock-first?" section:

```markdown
## 为什么选择 Mock-first？

许多研究仓库因为缺少 checkpoint、数据集过大、环境冲突或预处理步骤缺失而难以直接运行。

因此 PaperPilot 采用 mock-first 的产品化策略：

1. **理解**论文和可选仓库
2. **识别**可行的产品场景
3. **生成**清晰的接口和适配器边界
4. **默认使用 mock** — 原型无需真实模型即可运行
5. **后续集成** — 真实模型接入作为一个需要审查的工程步骤

这使得生成的原型安全、快速可运行，适合课程演示或早期产品验证。
```

- [ ] **Step 5: Run syntax check on all changed files**

```bash
python -c "import ast; ast.parse(open('tools/repo_scanner.py').read())"
python -c "import ast; ast.parse(open('tools/pdf_parser.py').read())"
```

- [ ] **Step 6: Run all tests to verify nothing is broken**

```bash
pytest -q
```
Expected: All tests pass

- [ ] **Step 7: Commit README changes**

```bash
git add README.md README_ZH.md
git commit -m "docs: add CI badge, restructure features, add mock-first philosophy section"
```
