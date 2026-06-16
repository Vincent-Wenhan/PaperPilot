# Code Review Rules

Rules for evaluating generated reproduction code quality.

## Scoring Guidelines

Each dimension is scored 1.0 (worst) to 5.0 (best):

- **paper_fidelity**: Does the code implement the paper's stated method? Penalize missing core modules, incorrect architecture, or ignoring paper evidence. Award high marks when module boundaries match the paper's described components.
- **completeness**: Are all method modules and dataflow steps from the paper covered? Missing modules, incomplete preprocessing, or omitted training loops reduce the score.
- **correctness**: Are formulas translated correctly? Are tensor shapes compatible? Are loss functions and optimizers appropriate for the stated objective terms? Penalize obvious logical errors.
- **runnability**: Does the code have valid `requirements.txt` or equivalent? Does `main.py --help` work without errors? Is there a smoke test with synthetic data? Are imports resolvable?

## Verdict Rules

- **overall_score >= 3.5**: verdict = "accept"
- **overall_score < 3.5**: verdict = "revise"

## Constraints

- Do not penalize for using mock-mode or placeholder stubs when the reproduction plan explicitly calls for them.
- Do not increase scores based on assumptions about unavailable hardware, datasets, or model checkpoints.
- Always provide at least one `revision_suggestion` when verdict is "revise".
