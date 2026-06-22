# Adapter Integration Rules

Generated prototypes use a mock-first `ModelAdapter` boundary. UI code plans
inputs and displays outputs; backend adapter code owns inference mode and
result shape.

## File responsibilities

- `manifest.json`: inventory of generated files, entrypoints, endpoints, run
  commands, and mock-first status.
- `frontend/`: browser UI code, product workflow, result display, and optional
  local mock adapter for offline preview.
- `backend/`: FastAPI service, request/response boundary, and model adapter.
- `backend/adapter.py`: `setup`, `load_model`, `predict`, and `mock_mode`
  handling.
- `requirements.txt`: backend dependencies needed to launch the generated
  adapter service.
- `README.md`: run instructions, limitations, and manual integration notes.

## Mock-first defaults

- Default `mock_mode=true`.
- Mock results must match the selected `template_type` (`image`, `text`,
  `video`, or `file`).
- Mock output must be deterministic and clearly labeled as demo behavior.

## Real integration boundaries

- Do not import or execute the analyzed repository automatically.
- Real integration requires manual review of inference code and explicit user
  action to disable mock mode.
- Use `NotImplementedError` or a clear API error for unreviewed real-model
  paths instead of guessing imports or weights.
- Never download checkpoints, install extra packages, or run shell commands from
  generated prototype code.

## Safety

Productize Mode may only write generated prototype files under
`generated_product/` or the current `workspace/runs/<run_id>/generated_product/`.
Generated adapters must not modify analyzed repositories.
