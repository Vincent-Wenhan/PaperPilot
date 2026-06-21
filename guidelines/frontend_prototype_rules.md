# Frontend Prototype Rules

Use the frontend that best fits the product workflow. PaperPilot's deterministic
Productize scaffold defaults to a static browser bundle, but a generated plan
may recommend React, Vue, Svelte, Streamlit, or another tool only when the
choice is justified by the target user and MVP scope.

- Keep the first screen as the usable workflow, not a landing page.
- Provide visible domain-specific controls, clear empty/loading/success/error
  states, and a structured result view.
- Keep mock mode explicit and safe. Do not run repository scripts, download
  weights, train models, or call external services from the prototype.
- Include evidence, limitations, and export/download behavior.
- Avoid raw JSON as the only user-facing result.
