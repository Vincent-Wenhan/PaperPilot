# Safety Rules

Agents reason and plan; deterministic tools perform actions. Productize Mode
may only write generated prototype files. Generated adapters default to mock
mode and do not import or execute analyzed repositories. Do not download
datasets, models, or weights. Never use `shell=True` or arbitrary commands.
