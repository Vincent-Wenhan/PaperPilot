# Optional GitHub URL and Code Agent - Design Document

> 2026-06-10

## Problem

PaperPilot currently requires a public GitHub repository before it can analyze
code, plan an environment, or recommend experiments. This blocks reproduction
work for papers whose implementation is closed-source or unavailable.

## Design

Make the GitHub URL optional and route repository acquisition through one of
two paths after paper and method analysis:

1. When a GitHub URL is provided, validate, shallow-clone, and scan it as
   before.
2. When the URL is empty, ask Code Agent to generate a minimal reproduction
   project from the paper text excerpt, paper summary, method breakdown,
   hardware, and selected goal.

Both paths produce a local repository path and use the existing read-only
repository scanner. Environment, experiment, Runner, and report stages
therefore continue to use the same downstream contract.

## Code Agent Output

Code Agent must return one JSON object containing:

- a short project name
- a summary that identifies simplifications and uncertainty
- a list of text files with relative paths and complete contents

The generated project should include a README and a lightweight entry point
that supports `python main.py --help` without downloads, training, or external
service calls.

## Safety

Generated files are written under a unique
`workspace/generated_reproduction_*` directory.

The writer rejects:

- absolute paths and parent-directory traversal
- `.git` and internal manifest targets
- Windows reserved names and unsafe path characters
- duplicate paths
- more than 20 files
- more than 500,000 total generated characters

Generated code is not executed automatically. The existing Runner allowlist
still controls all user-triggered commands.

## Files

| File | Change |
|---|---|
| `agents/code_agent.py` | Generate, validate, and materialize reproduction projects |
| `agents/__init__.py` | Export Code Agent |
| `prompts/code_prompt.txt` | Define the structured code-generation contract |
| `main.py` | Route optional URL to clone or code generation |
| `app.py` | Mark GitHub URL optional and display code-generation results |
| `prompts/*.txt` | Distinguish generated code from official implementations |
| `README.md`, `README_ZH.md` | Document the new workflow |
| `tests/test_code_agent.py` | Cover safe writing and both routing paths |

## Non-Goals

- Claiming that generated code is the paper's official implementation
- Claiming that generated code reproduces reported metrics
- Automatically executing training or downloading datasets/checkpoints
- Supporting authenticated private repository cloning

## Verification

1. Run `python -m compileall -q agents tools main.py app.py tests`.
2. Run `python -m unittest discover -s tests -v`.
3. Import `app` and `main`.
4. Verify an empty URL creates a generated repository in Mock Mode.
5. Verify a provided URL keeps the clone path and does not call Code Agent.
6. Verify path traversal and Windows reserved names are rejected.
