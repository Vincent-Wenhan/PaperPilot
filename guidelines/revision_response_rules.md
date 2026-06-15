# Revision Response Rules

When evaluation scores are below 4.0 or revision is requested, improve clarity,
scope discipline, and evidence quality before adding new capabilities.

## Revision priorities

1. Fix unsupported claims and missing limitations.
2. Narrow MVP scope or simplify user flow.
3. Align prototype inputs/outputs with the approved PRD.
4. Improve traceability from features to paper evidence.

## Bounded changes

Within one revision cycle:

- do not expand `must_have` scope unless evaluation identified a blocking gap,
- do not add training, repo execution, or automatic real-model integration,
- do not raise scores by assuming unavailable models, datasets, or checkpoints.

## Response format

Address each `revision_suggestions` item explicitly. State what changed, what
remains mock-only, and which limitations are still unresolved.

## Evaluator alignment

Re-score only after verifying the revision against the approved rubric,
confidence labels, and safety rules.
