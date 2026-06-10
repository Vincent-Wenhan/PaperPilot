# Functional Upgrade MVP Implementation Plan

## Goal

Implement the minimum viable upgrade described in
`docs/PaperPilot_Functional_Upgrade_Plan.md` without breaking the existing
Reproduce Mode or existing Productize callers.

The upgraded Productize Mode will support one or more papers, use a small set
of high-level agents, produce structured capability/composition/product
artifacts, and evaluate the generated mock-first prototype against a rubric.

## Compatibility Boundary

- Keep `run_paperpilot()` and Reproduce Mode behavior unchanged.
- Keep the existing `run_productize_pipeline()` parameters valid.
- Keep the five legacy Productize agents available during migration.
- Keep deterministic scaffold generation, backup, inspection, and mock mode.
- Do not execute analyzed repositories or download models, datasets, or
  weights.

## Implementation Slices

### 1. Guidelines and Loader

Add `guidelines/` documents for:

- multi-paper composition,
- product design principles,
- PRD and JTBD,
- value proposition,
- MVP and MoSCoW scope,
- product evaluation,
- Streamlit UI,
- safety,
- reproduction checks.

Add `tools/guideline_loader.py` with project-local path validation and UTF-8
loading.

### 2. Structured Schemas

Add schemas for:

- paper capability cards,
- paper relationships and method composition,
- PRD, MVP scope, and product plan,
- prototype plans,
- rubric-based product evaluation.

All score fields will be bounded and all optional collections will have safe
defaults.

### 3. Four High-Level Productize Agents

Add:

- `ResearchSynthesizerAgent`,
- `ProductPlannerAgent`,
- `PrototypeBuilderAgent`,
- `ProductEvaluatorAgent`.

Each agent receives the relevant guidelines. Mock mode returns deterministic,
schema-valid output. Real LLM mode requires JSON matching the schema and falls
back safely when parsing fails.

### 4. Productize Pipeline Upgrade

Extend the existing product pipeline to:

1. normalize single-paper and multi-paper inputs,
2. produce capability cards and a method composition plan,
3. produce a PRD-driven product plan with JTBD, value proposition, MVP, and
   MoSCoW,
4. produce a prototype plan,
5. generate and inspect the deterministic mock-first prototype,
6. evaluate it against the product rubric,
7. preserve legacy result keys and partial-stage error handling.

### 5. Multi-Paper UI and Documentation

- Allow Productize Mode to upload multiple PDFs.
- Build or reuse reproduction context per paper without changing Reproduce
  Mode.
- Display capability cards, composition, PRD/MVP, prototype plan, and
  evaluation.
- Update English and Chinese READMEs and development architecture notes.

## Tests

- Guideline loading and path validation.
- Schema validation and bounded scores.
- High-level agent mock outputs.
- Single-paper backward compatibility.
- Multi-paper pipeline composition and evaluation.
- Multi-paper UI helper behavior.
- Full regression suite, compile checks, and `git diff --check`.

## Delivery

Development occurs on `feat/functional-upgrade`. Commits follow Conventional
Commits and the branch remains ready for squash merge into `master`.
