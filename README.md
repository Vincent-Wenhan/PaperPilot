# PaperPilot 2.0

[![GitHub](https://img.shields.io/badge/GitHub-Vincent--Wenhan/PaperPilot-181717?logo=github)](https://github.com/Vincent-Wenhan/PaperPilot) · [中文版](README_ZH.md)

PaperPilot 2.0 is a multi-agent paper reproduction and product prototyping assistant. Users upload a paper PDF and optionally provide a GitHub repository. Reproduce Mode analyzes the method and code to produce an actionable reproduction plan. Productize Mode then identifies realistic applications, recommends an MVP, and generates a limited-scope Streamlit prototype with a unified, mock-first `ModelAdapter`.

The project extends **Paper-to-Reproduce** into **Paper-to-Product** without presenting itself as a universal product generator. When a real model interface cannot be determined safely, the generated prototype remains demonstrable through mock mode.

## Project Positioning

This AIGC course project demonstrates how a lightweight, interpretable multi-agent pipeline can assist both paper reproduction and bounded application prototyping. It does not promise automatic full training, paper-result equivalence, or production-ready model integration.

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

## System Architecture

```text
Paper PDF + GitHub URL (optional)
↓
Reproduce Mode
├── Paper and method analysis
├── Repository acquisition and analysis
├── Environment and experiment planning
└── Reproduction outputs
↓
Productize Mode
├── Product Opportunity Agent
├── Product Designer Agent
├── Template selection
├── Tech Adapter Agent
├── Frontend Builder Agent
├── Deterministic product scaffold
└── Product inspection and Product Test Agent
↓
generated_product/
```

## Agent Overview

| Agent | Responsibility |
| --- | --- |
| Paper Reader Agent | Extract task, contributions, datasets, metrics, and experimental settings |
| Method Extractor Agent | Decompose method into implementable modules, training and inference pipelines |
| Repo Clone Agent | Deterministically call GitHub clone tool; does not execute repository code |
| Code Agent | Generate a minimal, inspectable reproduction project when no GitHub URL is provided |
| Repo Analyzer Agent | Analyze repository structure, dependencies, configurations, and entry points |
| Environment Agent | Generate environment recommendations based on dependency evidence and hardware |
| Experiment Planner Agent | Generate Level 0 to Level 4 hierarchical reproduction roadmaps |
| Runner Agent | Deterministically invoke the safe command runner |
| Debug Agent | Analyze command, stdout, stderr, and environment information |
| Report Agent | Aggregate stage results and generate the reproduction report |
| Product Opportunity Agent | Identify capabilities, three application ideas, scores, and an MVP |
| Product Designer Agent | Convert the selected MVP into a bounded product specification |
| Tech Adapter Agent | Plan real integration without inventing or executing repository APIs |
| Frontend Builder Agent | Design a simple template-specific Streamlit interaction |
| Product Test Agent | Explain deterministic product inspection results and limitations |

All LLM agents share `BaseAgent` and a unified OpenAI-compatible `LLMClient`. Command execution and repository cloning are not LLM-decided.

## Project Structure

```text
PaperPilot/
├── app.py
├── main.py
├── config.py
├── agents/
├── productize/
├── tools/
├── prompts/
├── uploads/
├── workspace/
├── outputs/
│   ├── reproduction_plan.md
│   ├── run.sh
│   └── report.md
├── generated_product/       # Runtime-generated, gitignored prototype
├── requirements.txt
└── README.md
```

## Installation

The project is developed on WSL with Python 3.12. A dedicated Conda environment is recommended:

```bash
cd <path/to/PaperPilot>
conda create -n paperpilot python=3.12 -y
conda run -n paperpilot python -m pip install --upgrade pip
conda run -n paperpilot python -m pip install -r requirements.txt
```

Verify dependencies:

```bash
conda run -n paperpilot python -m pip check
conda run -n paperpilot python -c "import fitz, streamlit, openai; print('imports ok')"
```

## Running

```bash
cd <path/to/PaperPilot>
conda run -n paperpilot streamlit run app.py
```

Open the local address output by Streamlit in your browser. The application entry is `app.py`; the core orchestration function is `run_paperpilot()` in `main.py`.

## Mock Mode

The project defaults to mock mode (no API key needed). Mock mode is controlled via the **Mock Mode** toggle in the Streamlit sidebar.

Mock mode returns fixed text, but PDF parsing, URL validation, repository cloning, scanning, output file generation, and the secure Runner still go through the real local pipeline. The page will not crash without an API key.

## Real LLM API

`LLMClient` uses the OpenAI-compatible Chat Completions API. Configure credentials directly in the Streamlit **sidebar**:

| Sidebar Field | Description |
|---|---|
| API Key | Your OpenAI-compatible API key (password-masked) |
| Base URL | Endpoint URL, defaults to `https://api.openai.com/v1` |
| Model | Model name, defaults to `gpt-4o-mini` |
| Mock Mode | Toggle on/off — when enabled, no API call is made |

Alternatively, you may still use environment variables (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_MOCK_MODE`) — sidebar values take precedence. Do not write API keys into code or commit them to the repository.

## Reproduce Mode

1. Upload a paper PDF.
2. Optionally enter a repository URL in `https://github.com/owner/repository` format. Leave it empty to generate code from the paper.
3. Select `CPU only`, `Single GPU`, or `Multi GPU`; optionally enter a GPU model.
4. Select a goal: understand the paper, run the official demo, minimal training experiment, reproduce main experiments, or debug errors.
5. Click `Analyze` to view agent status and stage results.
6. Download `reproduction_plan.md`, `run.sh`, and `report.md`.
7. In the Runner section, click safe commands manually; automatic debugging appears on failure.
8. In the Debug section, paste logs for independent diagnosis.

## Productize Mode

Productize Mode reuses the current session's paper, method, repository
analysis, and repository path. If no complete analysis is available, it
automatically runs the existing `run_paperpilot()` repository-analysis path
before product generation.

1. Select **Productize Paper** in the sidebar.
2. Upload a PDF and optionally provide a GitHub URL when no reusable analysis exists.
3. Enter the target user and product goal.
4. Choose `Auto`, `Image`, `Text`, `Video`, or `File`.
5. Click **Generate Product Prototype**.
6. Review product opportunities, the MVP specification, adapter plan, frontend plan, generated files, and test report.

The generated bundle contains:

```text
generated_product/
├── app.py
├── adapter.py
├── README.md
├── product_spec.md
├── requirements.txt
└── outputs/
```

Existing output is moved to a timestamped `generated_product_backup_*`
directory before a replacement is written.

Run the prototype:

```bash
cd generated_product
pip install -r requirements.txt
streamlit run app.py
```

The generated adapter defaults to `mock_mode=True`. Real integration requires
manual review and edits to `adapter.py`; PaperPilot does not import or execute
the analyzed repository automatically.

## Example Input

- Example PDF: any text-extractable paper PDF uploaded by the user
- Example GitHub URL: `https://github.com/octocat/Hello-World`
- Example hardware: `CPU only` or `Single GPU`
- Example goal: `run official demo` or `minimal training experiment`

The example repository is used only to demonstrate shallow cloning and scanning; it does not contain a machine learning training pipeline. Avoid using large deep learning repositories for quick classroom demonstrations.

## Runner Security Policy

The Runner only executes lightweight commands after a user clicks a button:

- `python --version`
- `pip --version`
- `python <entrypoint> --help` for detected entry points

Security measures include:

- Precise allowlist as primary protection, blacklist as secondary
- Uses `shlex.split` and calls `subprocess.run` with a list argument
- `shell=True` is prohibited
- Pipes, redirects, semicolons, `&&`, and `||` are prohibited
- Blocks `sudo`, `rm -rf`, `mkfs`, `shutdown`, `reboot`, `curl`, `wget`, `chmod 777`, and fork bombs
- `cwd` is restricted to the project directory or `workspace/`
- Every command has a timeout
- stdout and stderr are truncated to the last 4000 characters

The Runner will not execute full training, demo bodies, unknown shell scripts, or download large datasets by default.

## Debug Capabilities

When a Runner command fails, the system automatically forwards the command, cwd, return code, stdout, and stderr to the Debug Agent. Users can also manually paste commands, logs, and environment information. The Debug Agent outputs the direct cause, possible root cause, verification method, fix suggestions, and next steps. Mock mode also returns presentable mock diagnostics.

## Output Files

- `outputs/reproduction_plan.md`: paper, method, repository, environment, experiment roadmap, checklist, and risks
- `outputs/run.sh`: contains only safe default commands and TODO comments
- `outputs/report.md`: structured reproduction report suitable for course project presentation

Mock example outputs are provided in the repository. Each pipeline run overwrites these files.

Product prototypes are runtime artifacts under `generated_product/` and are
gitignored. The main application displays their contents after generation.

## Limitations

- Scanned PDFs without OCR may yield no extractable text.
- LLM output quality depends on the model, context length, and paper text quality.
- Code Agent output is an independent approximation and is not the paper's official implementation.
- Repository analysis is based on static file scanning and may not automatically understand all custom entry points.
- The system does not verify whether full training achieves the original paper's metrics.
- The Runner intentionally uses a strict allowlist and does not provide arbitrary terminal capabilities.
- Real APIs, private repositories, datasets, and checkpoints may require manual user configuration.
- Product idea quality depends on the available paper and static repository evidence.
- Template selection supports only image, text, video, and generic file-analysis prototypes.
- Generated adapters do not guarantee that a research model can be integrated without manual engineering.
- Mock results demonstrate the product workflow; they are not paper-model predictions.

## Future Improvements

- Add OCR and table/formula parsing for papers
- Add configurable repository scan depth and dependency conflict analysis
- Introduce human-confirmed controlled demo execution
- Save multiple reproduction sessions and experiment comparisons
- Add structured output validation for real models
- Add unit tests, CI, and containerized release

---

> [中文版](README_ZH.md)
