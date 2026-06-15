# Product Selection Rules

Score each `ProductOpportunity` from 1 to 5 using the anchors below, then select
one feasible mock-first product. Reject options that cannot be demonstrated
safely within MVP scope.

## Score anchors

- `1`: unsupported, unsafe, or not traceable to paper evidence.
- `3`: partially supported; demo possible only with clear limitations.
- `5`: strongly supported, simple to demo, and mock-first friendly.

## Dimension guidance

- `paper_faithfulness`: alignment with cited paper capabilities.
- `multi_paper_coherence`: compatibility of selected papers and workflow.
- `demo_feasibility`: can a short Streamlit demo show the core job?
- `mock_first_suitability`: can the MVP work without real model integration?
- `integration_risk`: lower is better; high risk should reduce overall score.
- `course_presentation_value`: clarity for a classroom or project demo.

## Hard gates

Do not select a product when:

- `paper_faithfulness` is below 3,
- the core workflow depends on unavailable models, data, or checkpoints,
- the plan requires training, arbitrary command execution, or automatic repo
  execution,
- multiple papers conflict without an explicit composition strategy.

## Selection output

`selection_reason` must name the chosen product, the top supporting evidence,
and why stronger-scoring alternatives were excluded.
