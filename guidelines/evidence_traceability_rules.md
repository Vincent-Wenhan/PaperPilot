# Evidence and Traceability Rules

Use only supplied paper text, repository scan results, and explicit user input.
Never invent capabilities, datasets, metrics, checkpoints, URLs, or integration
steps.

## Valid evidence

- Paper text with a `[Page N]` marker or an equivalent page-specific citation.
- Exact HTTPS URLs that appear verbatim in the paper or repository evidence.
- Repository scan facts such as README instructions, dependency files, and named
  entry points.
- User-provided goals, hardware notes, or corrections.

## Invalid or weak evidence

- Title, author list, or abstract alone for detailed technical claims.
- Guessed URLs, repaired links, or inferred download locations.
- Assumed model weights, private datasets, or unavailable APIs.
- Claims that a repository behavior works without scan or execution evidence.

## Traceability chain

Every product feature, capability card field, composition step, and prototype
input/output must trace back to at least one evidence item. When the chain is
incomplete, mark the item as `unknown` or move it to limitations instead of
presenting it as proven.

## Missing information

List unresolved details under `missing_information`, `limitations`, or
`risks`. Do not fill gaps with plausible but unsupported technical detail.
