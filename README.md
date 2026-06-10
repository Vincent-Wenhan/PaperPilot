# AIGC_PaperPilot / PaperPilot

[![GitHub](https://img.shields.io/badge/GitHub-Vincent--Wenhan/PaperPilot-181717?logo=github)](https://github.com/Vincent-Wenhan/PaperPilot) · [中文版](README_ZH.md)

PaperPilot is a multi-agent paper reproduction assistant for ML research novices. Traditionally, reproducing a paper requires repeatedly reading the paper, finding code, setting up the environment, understanding experimental configurations, and debugging errors — a complex process that often fails. This project decomposes paper reproduction into stages: paper reading, method decomposition, code repository analysis, environment setup, experiment planning, safe execution, error diagnosis, and report generation. Multiple specialized agents collaborate to complete these tasks. Users simply upload a paper PDF and provide a GitHub repository link, and the system generates a structured reproduction roadmap, experiment checklist, run commands, and debug suggestions.

## Project Positioning

This is an AIGC course final project demonstrating how a lightweight, interpretable multi-agent pipeline can assist paper reproduction. PaperPilot is neither a fully automated training system nor a simple paper summarizer. It connects paper comprehension, code analysis, environment planning, minimal experimentation, safe execution, error diagnosis, and report generation — prioritizing an actionable reproduction starting point for the user.

## Features

- Upload and parse paper PDFs
- Validate and shallow-clone public GitHub repositories
- Scan README, dependency files, configurations, and candidate entry points
- Generate paper summaries and engineering-oriented method breakdowns
- Plan environments based on CPU, single-GPU, or multi-GPU
- Generate hierarchical experiment roadmaps, checklists, and safe `run.sh`
- Run version checks and `--help` on lightweight candidate commands
- Automatically analyze Runner failures; also supports manual log pasting for debugging
- Generate and download reproduction plans, scripts, and course-project reports
- Full demo via mock mode without any API key

## System Architecture

```text
User Input
├── Paper PDF
├── GitHub URL
├── Hardware Info
└── Reproduction Goal
↓
PDF Parser + GitHub Clone + Repo Scanner
↓
Multi-Agent Pipeline
├── Paper Reader Agent
├── Method Extractor Agent
├── Repo Analyzer Agent
├── Environment Agent
├── Experiment Planner Agent
├── Runner Agent
├── Debug Agent
└── Report Agent
↓
Outputs
├── reproduction_plan.md
├── run.sh
└── report.md
```

## Agent Overview

| Agent | Responsibility |
| --- | --- |
| Paper Reader Agent | Extract task, contributions, datasets, metrics, and experimental settings |
| Method Extractor Agent | Decompose method into implementable modules, training and inference pipelines |
| Repo Clone Agent | Deterministically call GitHub clone tool; does not execute repository code |
| Repo Analyzer Agent | Analyze repository structure, dependencies, configurations, and entry points |
| Environment Agent | Generate environment recommendations based on dependency evidence and hardware |
| Experiment Planner Agent | Generate Level 0 to Level 4 hierarchical reproduction roadmaps |
| Runner Agent | Deterministically invoke the safe command runner |
| Debug Agent | Analyze command, stdout, stderr, and environment information |
| Report Agent | Aggregate stage results and generate the reproduction report |

All LLM agents share `BaseAgent` and a unified OpenAI-compatible `LLMClient`. Command execution and repository cloning are not LLM-decided.

## Project Structure

```text
AIGC_PaperPilot/
├── app.py
├── main.py
├── config.py
├── agents/
├── tools/
├── prompts/
├── uploads/
├── workspace/
├── outputs/
│   ├── reproduction_plan.md
│   ├── run.sh
│   └── report.md
├── requirements.txt
└── README.md
```

## Installation

The project is developed on WSL with Python 3.12. A dedicated Conda environment is recommended:

```bash
cd /home/fcc/projects/AIGC_PaperPilot
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
cd /home/fcc/projects/AIGC_PaperPilot
conda run -n paperpilot streamlit run app.py
```

Open the local address output by Streamlit in your browser. The application entry is `app.py`; the core orchestration function is `run_paperpilot()` in `main.py`.

## Mock Mode

The project defaults to `LLM_MOCK_MODE=True`, requiring no API key:

```bash
export LLM_MOCK_MODE=True
conda run -n paperpilot streamlit run app.py
```

Mock mode returns fixed text, but PDF parsing, URL validation, repository cloning, scanning, output file generation, and the secure Runner still go through the real local pipeline. The page will not crash without an API key.

## Real LLM API

`LLMClient` uses the OpenAI-compatible Chat Completions API. Set these before launching:

```bash
export LLM_MOCK_MODE=False
export LLM_API_KEY="your-api-key"
export LLM_MODEL="your-model-name"
export LLM_BASE_URL="https://your-compatible-endpoint/v1"
conda run -n paperpilot streamlit run app.py
```

When using the default OpenAI endpoint, `LLM_BASE_URL` can be omitted. Do not write API keys into code or commit them to the repository. When no key is configured, the client returns a clear message instead of crashing.

## Streamlit Usage

1. Upload a paper PDF.
2. Enter a repository URL in `https://github.com/owner/repository` format.
3. Select `CPU only`, `Single GPU`, or `Multi GPU`; optionally enter a GPU model.
4. Select a goal: understand the paper, run the official demo, minimal training experiment, reproduce main experiments, or debug errors.
5. Click `Analyze` to view agent status and stage results.
6. Download `reproduction_plan.md`, `run.sh`, and `report.md`.
7. In the Runner section, click safe commands manually; automatic debugging appears on failure.
8. In the Debug section, paste logs for independent diagnosis.

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

## Limitations

- Scanned PDFs without OCR may yield no extractable text.
- LLM output quality depends on the model, context length, and paper text quality.
- Repository analysis is based on static file scanning and may not automatically understand all custom entry points.
- The system does not verify whether full training achieves the original paper's metrics.
- The Runner intentionally uses a strict allowlist and does not provide arbitrary terminal capabilities.
- Real APIs, private repositories, datasets, and checkpoints may require manual user configuration.

## Future Improvements

- Add OCR and table/formula parsing for papers
- Add configurable repository scan depth and dependency conflict analysis
- Introduce human-confirmed controlled demo execution
- Save multiple reproduction sessions and experiment comparisons
- Add structured output validation for real models
- Add unit tests, CI, and containerized release

---

> [中文版](README_ZH.md)
