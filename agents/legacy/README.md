# Legacy Agents

These fragmented agents are retained only as migration references and for
isolated compatibility tests. They are not exported from `agents`, and active
Reproduce/Productize pipelines must not import or call them.

New reasoning behavior belongs in one of the eight high-level agents in the
parent directory. Deterministic actions belong in `tools/`, `pipeline/`, or
`productize/`.
