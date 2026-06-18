# Generation Protocol and Workbench Implementation Notes

## Goal

Implement the design in
`docs/superpowers/specs/2026-06-18-generation-protocol-workbench-design.md`.
The work introduces structured generation protocols for Reproduce and
Productize, then uses those protocols to improve generated artifacts and host
UI review surfaces.

## Planned Scope

- Add `ImplementationBlueprint` to guide generated reproduction projects.
- Add deterministic blueprint construction and blueprint coverage checks.
- Add `ProductUISpec` to guide generated product Streamlit apps.
- Render generated product apps from structured UI spec fields.
- Add Reproduce and Productize host UI summaries that present generated
  artifacts as inspectable work products before raw JSON or source listings.

## Compatibility and Safety

- Existing public result keys remain stable; new keys are additive.
- Existing `scaffold_product()` callers continue to work without `ui_spec`.
- Generated adapters remain mock-first and never execute analyzed repositories.
- Static inspection continues to compile and inspect files without launching
  Streamlit.

## Verification

Implementation must use test-first development and finish with:

```bash
conda run -n paperpilot python -m pytest -q
```
