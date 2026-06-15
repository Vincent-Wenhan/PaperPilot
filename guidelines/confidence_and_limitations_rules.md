# Confidence and Limitations Rules

Label important claims with one confidence level and keep the same label across
PRD, MVP scope, prototype plan, evaluation, and UI copy.

## Confidence levels

- `proven`: directly supported by paper or repository evidence.
- `inferred`: reasonable interpretation with cited supporting evidence.
- `assumed`: productization choice not validated by the paper or repository.
- `mock`: placeholder behavior for demo only; not a real model capability.

## Required disclosures

Every product plan and prototype must state:

- what is demonstrated in mock mode,
- what would require manual real integration,
- what data, checkpoints, or hardware are unavailable,
- what paper claims are not reproduced in the MVP.

## Wording rules

- Do not describe mock output as a real prediction or benchmark result.
- Do not upgrade `inferred` or `assumed` items to `proven` without new evidence.
- Prefer explicit limitations over broad marketing language.
- If confidence is below `proven`, say so in PRD `limitations` and prototype
  captions.
