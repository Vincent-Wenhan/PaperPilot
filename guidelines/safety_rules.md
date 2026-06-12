# Safety Rules

Agents reason and plan; deterministic tools perform actions. Productize Mode
may only write generated prototype files. Generated adapters default to mock
mode and do not import or execute analyzed repositories. Reproduce Mode may
generate a Python data-download script only for exact HTTPS links found in the
paper or repository evidence. Download scripts must default to dry-run, require
explicit `--execute`, and must never be executed automatically. Never use
`shell=True` or arbitrary commands.
