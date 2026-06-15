# PaperPilot 2.0

[![GitHub](https://img.shields.io/badge/GitHub-Vincent--Wenhan/PaperPilot-181717?logo=github)](https://github.com/Vincent-Wenhan/PaperPilot) · [中文版](README_ZH.md)
![CI](https://github.com/Vincent-Wenhan/PaperPilot/actions/workflows/ci.yml/badge.svg)

PaperPilot 2.0 is a theory-guided, safety-bounded multi-agent system for paper reproduction and research-to-product prototyping. Users can upload one or multiple papers and optionally provide GitHub repositories. Reproduce Mode analyzes methods and code to produce actionable reproduction plans. Productize Mode extracts paper capability cards, composes compatible methods, creates a PRD-driven MVP, and generates a limited-scope Streamlit prototype with a unified, mock-first `ModelAdapter`.

The project extends **Paper-to-Reproduce** into **Paper-to-Product** without presenting itself as a universal product generator. When a real model interface cannot be determined safely, the generated prototype remains demonstrable through mock mode.

## Project Positioning

This Large AI Models course project demonstrates how a lightweight, interpretable multi-agent pipeline can assist both paper reproduction and bounded application prototyping. It does not promise automatic full training, paper-result equivalence, or production-ready model integration.

## Features

PaperPilot combines paper understanding, repository analysis, reproduction planning, and product prototyping in a single workflow. See [`examples/`](examples/sample_outputs/) for sample outputs.

### Reproduce Mode

- Upload and parse paper PDFs
- Optionally validate and shallow-clone public GitHub repositories
- Generate an independent minimal reproduction project when requested
- Scan README, dependency files, configurations, and candidate entry points
- Generate paper summaries and engineering-oriented method breakdowns
- Reconstruct module dataflow, objectives, experiment findings, and an implementation blueprint
- Generate a separate runnable reproduction project with synthetic smoke tests
- Generate a reviewed, dry-run-first Python downloader when exact dataset or checkpoint HTTPS links are found in paper or repository evidence
- Plan environments based on CPU, single-GPU, or multi-GPU
- Generate hierarchical experiment roadmaps, checklists, and safe `run.sh`
- Classify candidate commands as safe, review, or blocked without executing them
- Execute commands through deterministic Runner tools and analyze failures with the Execution & Diagnosis Agent
- Generate and download reproduction plans, scripts, and course-project reports

### Productize Mode

- Accept one or multiple paper PDFs with an optional shared or per-paper repository
- Generate Paper Capability Cards, a Capability Map, and Method Composition Plan
- Apply JTBD, Value Proposition Canvas, PRD, MVP, and MoSCoW scope rules
- Produce a structured prototype plan and rubric-based product evaluation
- Select image, text, video, or generic file-analysis templates
- Generate an isolated Streamlit prototype under `generated_product/`
- Inspect generated files, Python syntax, mock mode, and run instructions

### Mock Mode

- Enable **Mock Mode** in the Streamlit sidebar or set `LLM_MOCK_MODE=true` to run the full pipeline without an API key
- By default (`LLM_MOCK_MODE=false`), real paper analysis requires an API key
- Generated **product prototypes** remain mock-first regardless — safe demo outputs without real model integration

## System Architecture

```text
Paper PDF(s) + GitHub URL(s) (optional)
↓
Reproduce Mode
├── LangGraph: parse paper
├── [parallel] Research Understanding + repository preparation
├── Repository Understanding Agent (joined evidence)
├── Reproduction Planner Agent + command risk routing
├── Reproduction Implementation Agent
├── Execution & Diagnosis Agent
└── Deterministic Report Builder
↓
Productize Mode
├── [Phase 1] LangGraph generate_proposals()
│   ├── Research Synthesizer Agent fan-out per paper
│   │   ├── Capability Cards and Capability Map
│   │   └── Method Composition Plan
│   └── Product Planner Agent
│       ├── JTBD and Value Proposition
│       └── PRD, MVP, and MoSCoW
├── [Review] User selects & edits a proposal
├── [Phase 2] LangGraph execute_proposal()
│   ├── Prototype Builder Agent
│   ├── Product Evaluator Agent + bounded revision routing
│   └── Final deterministic scaffold and static inspection
↓
generated_product/<product_name>/
```

## Agent Overview

| Agent | Responsibility |
| --- | --- |
| Research Understanding Agent | Merge paper reading and method extraction into one structured artifact |
| Repository Understanding Agent | Interpret static repository scans and environment evidence |
| Reproduction Planner Agent | Plan environment, data, experiments, safe commands, risks, and fallbacks |
| Reproduction Implementation Agent | Generate a bounded runnable implementation and smoke tests |
| Execution & Diagnosis Agent | Interpret command results and logs without executing commands |
| Research Synthesizer Agent | Build capability cards, relationships, and method composition plans |
| Product Planner Agent | Apply JTBD, Value Proposition, PRD, MVP, and MoSCoW |
| Prototype Builder Agent | Define the Streamlit flow, mock result, and adapter boundary |
| Product Evaluator Agent | Score paper faithfulness, coherence, safety, and demo readiness |

These are the only active reasoning agents. Fragmented predecessor agents are isolated under `agents/legacy/` and are not imported by active pipelines. Repository cloning/scanning, command execution, report writing, product scaffolding, and static inspection are deterministic tools or builders.

## Project Structure

```text
PaperPilot/
├── app.py
├── main.py
├── config.py
├── agents/                  # Nine active high-level agents
│   └── legacy/              # Inactive migration-reference agents
├── graphs/                  # Productize and Reproduce LangGraph workflows
├── runtime/                 # Graph state, routing, checkpoints, and tool runtime
├── guidelines/              # Product, composition, UI, and safety rules
├── schemas/                 # Structured paper, composition, product, and evaluation models
├── productize/
├── tools/
├── prompts/
├── uploads/
├── workspace/
├── outputs/                   # Per-paper outputs (outputs/<paper_name>/)
│   ├── reproduction_plan.md
│   ├── run.sh
│   └── report.md
├── generated_product/         # Runtime-generated prototypes (generated_product/<product_name>/)
├── examples/                  # Sample outputs illustrating pipeline results
├── requirements.txt
└── README.md
```

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
conda run -n paperpilot python -c "import fitz, langgraph, openai, streamlit, yaml; print('imports ok')"
```

## Running

```bash
cd <path/to/PaperPilot>
conda run -n paperpilot streamlit run app.py
```

Open the local address output by Streamlit in your browser. The application entry is `app.py`; the core orchestration function is `run_paperpilot()` in `main.py`.

## Mock Mode

Real LLM analysis is the default. Mock mode must be explicitly enabled with the
**Mock Mode** toggle in the Streamlit sidebar.

Mock mode validates PDF parsing, URL validation, repository cloning, scanning,
output generation, and the secure Runner, but no LLM reads the paper. Paper
analysis outputs are clearly labeled as placeholders.

## Real LLM API

`LLMClient` uses the OpenAI-compatible Chat Completions API. Configure credentials directly in the Streamlit **sidebar**:

| Sidebar Field | Description |
|---|---|
| API Key | Your OpenAI-compatible API key (password-masked) |
| Base URL | Endpoint URL, defaults to `https://api.openai.com/v1` |
| Model | Model name, defaults to `gpt-4o-mini` |
| Implementation Model | Optional stronger model used only for generated reproduction code |
| Mock Mode | Toggle on/off — when enabled, no API call is made |

Use **Test LLM Connection** in the sidebar before analysis to validate the
runtime dependency, Base URL, API key, model, and network/proxy path. Connection
failures stop repeated agent requests and are reported directly instead of
being mislabeled as invalid JSON.

Alternatively, you may still use environment variables (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_MOCK_MODE`) — sidebar values take precedence. Do not write API keys into code or commit them to the repository.

## Reproduce Mode

1. Upload a paper PDF.
2. Optionally enter a repository URL in `https://github.com/owner/repository` format.
3. Select `CPU only`, `Single GPU`, or `Multi GPU`; optionally enter a GPU model.
4. Select a goal: understand the paper, run the official demo, minimal training experiment, reproduce main experiments, or debug errors.
5. Click `Analyze` to view agent status and stage results.
6. Review and download the generated reproduction code ZIP, `reproduction_plan.md`, `run.sh`, and `report.md`.
7. In the Runner section, click safe commands manually; automatic debugging appears on failure.
8. In the Debug section, paste logs for independent diagnosis.

The Reproduce graph parses the paper once, prepares research and repository
evidence in parallel, then joins both branches for planning. Planned commands
are risk-classified and recorded as `executed=False`; the graph never runs them
automatically. Execution remains an explicit action in the Runner UI.

## Productize Mode

Productize Mode reuses current-session paper analysis when available. It also
supports multiple PDFs and can use no repository, one shared repository URL,
or exactly one repository URL per paper. If analysis is unavailable, it runs
the existing `run_paperpilot()` analysis path for each uploaded paper before
product generation.

1. Select **Productize Paper** in the sidebar.
2. Upload one or more PDFs.
3. Optionally provide one shared GitHub URL or one URL per paper on separate lines.
4. Enter the target user and product goal.
5. Choose `Auto`, `Image`, `Text`, `Video`, or `File`.
6. Click **Generate Proposals** to produce one or more product proposals.
7. Review proposals in tabs — each shows the full product plan (PRD, MVP/MoSCoW, risks, opportunities).
8. Select a proposal and optionally edit the core features and must-have scope.
9. Click **Execute Proposal** to generate the Streamlit prototype.
10. Review capability cards, composition plan, opportunities, PRD/MVP, prototype plan, generated files, and rubric evaluation.

The Productize pipeline is split into two backward-compatible LangGraph phases:

- **`generate_proposals()`** — fans out capability extraction per paper, synthesizes the merged evidence, and returns one `ProductProposal` per opportunity.
- **`execute_proposal()`** — evaluates and revises the selected plan at most once by default, then performs one final scaffold and inspection.

Existing single-paper callers of `run_productize_pipeline()` remain supported.
Existing Reproduce and Productize result keys also remain stable; graph-specific
trace, issue, revision, and command-review metadata are additive.

The generated bundle contains:

```text
generated_product/<product_name>/
├── app.py
├── adapter.py
├── README.md
├── product_spec.md
├── requirements.txt
└── outputs/
```

Run the prototype:

```bash
cd generated_product/<product_name>
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

Generated reproduction projects may include `scripts/download_data.py` only
when PaperPilot finds exact HTTPS dataset or checkpoint links in paper or
repository evidence. The script prints its plan by default, requires explicit
`--execute` for network access, and is never run automatically.

## Debug Capabilities

When a deterministic Runner command fails, the system forwards the command, cwd, return code, stdout, and stderr to the Execution & Diagnosis Agent. Users can also paste logs manually. The agent explains the direct cause, possible root causes, bounded fixes, and next actions; it never executes commands itself.

## Output Files

- `outputs/<paper_name>/reproduction_plan.md`: paper, method, repository, environment, experiment roadmap, checklist, and risks
- `outputs/<paper_name>/run.sh`: contains only safe default commands and TODO comments
- `outputs/<paper_name>/report.md`: structured reproduction report suitable for course project presentation

Each paper's outputs are saved in a separate directory named after the PDF filename.
Mock example outputs are provided in the repository (`outputs/` root fallback when no paper name is available).

Product prototypes are runtime artifacts under `generated_product/<product_name>/` and are
gitignored. The main application displays their contents after generation.

## Limitations

- Scanned PDFs without OCR may yield no extractable text.
- LLM output quality depends on the model, context length, and paper text quality.
- Paper-only planning cannot provide repository-specific implementation evidence.
- Repository analysis is based on static file scanning and may not automatically understand all custom entry points.
- The system does not verify whether full training achieves the original paper's metrics.
- The Runner intentionally uses a strict allowlist and does not provide arbitrary terminal capabilities.
- Real APIs, private repositories, datasets, and checkpoints may require manual user configuration.
- Product idea quality depends on the available paper and static repository evidence.
- Multi-paper composition is an evidence-backed plan, not proof that the real models integrate correctly.
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
