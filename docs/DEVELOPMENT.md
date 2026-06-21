# PaperPilot Development Notes

## Commit Style

Use Conventional Commits:

```text
<type>(<scope>): <subject>
```

Common scopes:

- `backend`: FastAPI routers and services
- `frontend`: Next.js workbench
- `pipeline`: Reproduce/Productize orchestration
- `productize`: product scaffold, templates, and inspection
- `reproduce`: reproduction planning and generated-code flow
- `agent`: active high-level agents
- `prompt`: prompt and guideline changes
- `docs`: documentation
- `test`: tests
- `config`: CI, dependencies, and project config

## Current Architecture

```text
Next.js Workbench -> FastAPI backend -> LangGraph pipelines
                                      -> deterministic tools/builders
```

The old Streamlit host UI has been removed. `main.py` remains the
backward-compatible Python orchestration entry point.

New workbench runs should keep artifacts under:

```text
workspace/runs/<run_id>/
  outputs/
  generated_product/
```

Backward-compatible direct pipeline calls may still write to `outputs/` or
`generated_product/`.

## Productize Output

Generated product prototypes are static browser bundles:

```text
index.html
app.js
adapter.js
styles.css
README.md
product_spec.md
outputs/
```

Do not reintroduce a hard Streamlit dependency for Productize. A prompt may
recommend a frontend framework only when the product need justifies it.

## Quality Rules

- Keep active reasoning agents high-level and structured.
- Generated reproduction code must have real implementation bodies, behavior
  assertions in tests, paper-specific names, and safe smoke-test paths.
- File writes and patches in the workbench must go through reviewable actions.
- Do not write API keys to repository config files.
- Do not run repository scripts, download weights, train models, or call
  networks from generated product prototypes.

## Verification

```bash
python -m compileall main.py config.py
python -m compileall agents tools pipeline productize schemas runtime graphs backend
python -m pytest tests/ -q
cd frontend && npm test && npm run build
```
