# PaperPilot Productize Mode Design

## Goal

Upgrade PaperPilot to PaperPilot 2.0 by adding a Productize Mode that turns
existing paper and repository analysis into a limited-scope Streamlit product
prototype. Reproduce Mode remains backward compatible and unchanged in its
public pipeline contract.

## Confirmed Product Decisions

- Productize Mode is independently selectable in the main Streamlit UI.
- When the current session has no reproduction analysis, Productize Mode
  automatically calls the existing `run_paperpilot()` pipeline first.
- Productization reuses `paper_info`, `method_info`, `repo_info`, and
  `repo_path` from the reproduction result.
- Generated product code is isolated under `generated_product/` and never
  modifies the analyzed repository.
- Generated adapters default to mock mode. Real model integration is an
  explicit manual task.
- Existing generated product content is backed up to a timestamped sibling
  directory before a new product is written.

## Architecture

The implementation adds a separate `productize` package beside the existing
reproduction pipeline. The Streamlit UI owns mode selection and decides whether
an existing reproduction result can be reused or must be generated. Once the
analysis context exists, the UI calls `run_productize_pipeline()`.

The Productize pipeline runs five focused agents:

1. Product Opportunity Agent identifies capabilities, three product ideas,
   scores, and a recommended MVP.
2. Product Designer Agent turns the recommendation into a product
   specification.
3. Tech Adapter Agent documents possible real-repository integration and the
   required mock fallback.
4. Frontend Builder Agent describes the Streamlit interaction.
5. Product Test Agent summarizes deterministic inspection results for the
   user.

Template selection, file generation, backups, syntax checks, and mock response
behavior are deterministic Python code. LLM output is advisory content and is
never executed.

## Components

### Agents and Prompts

Each new agent subclasses the existing `BaseAgent`, accepts the shared
`LLMClient`, and loads one prompt from `prompts/`. The agents return Markdown
and inherit the existing contained-failure behavior.

The new agents are exported from `agents/__init__.py` without changing existing
aliases or imports.

### Product Templates

`productize/product_templates.py` exposes:

```python
select_product_template(
    paper_info: str,
    method_info: str,
    repo_info: str,
    product_spec: str,
    preferred_type: str = "auto",
) -> str
```

An explicit preference wins when it is one of `image`, `text`, `video`, or
`file`. Automatic selection uses conservative keyword scoring over the analysis
and product specification. Ties and unknown domains fall back to `file`.

The module also provides deterministic Streamlit application source and mock
adapter response data for all four template types.

### Product Scaffold

`scaffold_product()` accepts the selected template, plans, repository path, and
an output directory. It:

1. validates the template and resolves the output path,
2. backs up an existing output directory,
3. creates `outputs/`,
4. writes `app.py`, `adapter.py`, `README.md`, `product_spec.md`, and
   `requirements.txt`,
5. returns paths relative to the generated product root where practical.

The generated application imports `ModelAdapter`, instantiates it with
`mock_mode=True`, renders template-specific inputs, catches prediction errors,
and offers downloadable JSON results. The adapter never executes shell
commands, downloads resources, trains a model, or imports the source repository
automatically. Real integration remains a documented `TODO`.

### Product Inspection

`inspect_generated_product()` checks required files and directories, compiles
`app.py` and `adapter.py` through Python's `py_compile` API, verifies mock-mode
markers, and checks that the README contains the run command. It returns
structured booleans, missing files, discovered files, notes, and compile errors.
It does not launch Streamlit.

### Product Pipeline

`run_productize_pipeline()` initializes a result containing all expected keys
plus an `errors` list. Every agent stage is isolated so a failed or empty result
is recorded without discarding earlier work.

If product design output is unavailable, the pipeline writes a deterministic
fallback product specification. It always selects a template and attempts to
scaffold a mock product. Deterministic inspection runs after scaffolding, and
its result is included in the Product Test Agent context.

The pipeline accepts `preferred_type="auto"`, an optional output directory, and
an optional progress callback while preserving the required core signature.

### Streamlit Integration

The sidebar contains:

```text
Reproduce Paper
Productize Paper
```

Reproduce Paper retains its current controls, outputs, downloads, Runner, and
Debug sections.

Productize Paper collects target user, product goal, and preferred product
type. On generation:

- reuse `st.session_state["paperpilot_result"]` when it contains the required
  analysis and repository path;
- otherwise validate the uploaded PDF, save it, and call `run_paperpilot()`
  using the existing repository URL and hardware controls;
- stop with clear errors only when no usable paper or repository analysis can
  be produced;
- call `run_productize_pipeline()` and store the result in session state.

The page displays opportunities, product specification, template type, adapter
plan, frontend plan, generated files, deterministic inspection, Product Test
Agent report, errors, and:

```bash
cd generated_product
streamlit run app.py
```

## Error Handling

- Agent initialization, execution, or empty output adds a stage-qualified error
  and leaves the rest of the pipeline runnable.
- Scaffold failures are reported and prevent inspection of a nonexistent
  bundle, but do not erase agent outputs.
- Backup and write failures are explicit; existing generated content is never
  silently overwritten.
- Automatic reproduction analysis uses existing `run_paperpilot()` error
  reporting.
- Generated applications catch adapter setup and prediction exceptions and
  display them with `st.error`.

## Security

- The analyzed repository is read-only from Productize Mode.
- Generated code is written only to the configured product output directory.
- The generated adapter defaults to mock mode and contains no subprocess or
  shell execution.
- No model weights, datasets, or dependencies are downloaded automatically.
- Real integration instructions require manual review of repository inference
  code and explicit adapter edits.
- Product testing performs file inspection and Python compilation only.

## Testing Strategy

Tests use `unittest`, temporary directories, and fake LLM clients to match the
existing suite.

- Agent tests verify prompt loading and mock-compatible execution.
- Template tests cover explicit preferences, image/text/video keyword
  selection, and the `file` fallback.
- Scaffold tests cover all four templates, required files, adapter mock
  responses, syntax compilation, and timestamped backup behavior.
- Inspector tests cover complete, missing, and syntactically invalid bundles.
- Pipeline tests cover a full mock run and an agent-failure path that still
  produces a mock product.
- UI helper tests cover detection of reusable analysis and automatic
  reproduction fallback inputs without launching a browser.
- The full existing test suite verifies Reproduce Mode compatibility.
- A Streamlit headless startup smoke check verifies the main app imports and
  starts without immediate exceptions.

## Documentation and Delivery

The English and Chinese READMEs will describe PaperPilot 2.0, both modes, the
generated product workflow, mock-mode limitations, and run commands.
`docs/DEVELOPMENT.md` will add `productize` as a commit scope and document the
new package boundary.

Implementation will be committed with Conventional Commits on
`codex/productize-mode`, pushed to `origin`, and opened as a draft pull request
against `master`.
