# Adapter Integration Rules

Generated prototypes use a mock-first `ModelAdapter` boundary. UI code plans
inputs and displays outputs; adapter code owns inference mode and result shape.

## File responsibilities

- `index.html`: browser mount point and static module wiring.
- `app.js`: layout, one primary action, result display, download.
- `adapter.js`: `setup`, `loadModel`, `predict`, and `mockMode` handling.
- `README.md`: run instructions, limitations, and manual integration notes.

## Mock-first defaults

- Default `mockMode=true`.
- Mock results must match the selected `template_type` (`image`, `text`,
  `video`, or `file`).
- Mock output must be deterministic and clearly labeled as demo behavior.

## Real integration boundaries

- Do not import or execute the analyzed repository automatically.
- Real integration requires manual review of inference code and explicit user
  action to disable mock mode.
- Use `NotImplementedError` for unreviewed real-model paths instead of guessing
  imports or weights.
- Never download checkpoints, install extra packages, or run shell commands from
  generated prototype code.

## Safety

Productize Mode may only write generated prototype files under
`generated_product/` or the current `workspace/runs/<run_id>/generated_product/`.
Generated adapters must not modify analyzed repositories.
