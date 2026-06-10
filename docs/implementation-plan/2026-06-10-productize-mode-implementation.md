# PaperPilot Productize Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backward-compatible Productize Mode that reuses or automatically creates paper analysis, generates a four-template mock-first Streamlit prototype, inspects it, and exposes the workflow in the main UI.

**Architecture:** Keep `run_paperpilot()` unchanged and add a separate `productize` package. The UI owns automatic reproduction fallback; the product pipeline owns agent orchestration; template selection, scaffolding, backup, and inspection remain deterministic.

**Tech Stack:** Python 3.12, Streamlit, pathlib, unittest, py_compile, existing BaseAgent and LLMClient.

---

## File Map

- `productize/product_templates.py`: template selection, mock responses, and generated Streamlit source.
- `productize/product_scaffold.py`: backup and generated-product file writing.
- `productize/product_tester.py`: deterministic completeness and syntax checks.
- `productize/product_pipeline.py`: resilient Productize orchestration.
- `agents/product_*_agent.py`: five BaseAgent wrappers.
- `prompts/product_*_prompt.txt`: five approved role prompts.
- `app.py`: mode selection, automatic analysis fallback, Productize controls and results.
- `tests/test_product_templates.py`: template and generated-source behavior.
- `tests/test_product_scaffold.py`: bundles, backups, adapters, and inspection.
- `tests/test_product_agents.py`: prompt loading and agent execution.
- `tests/test_product_pipeline.py`: complete and degraded pipeline behavior.
- `tests/test_productize_ui.py`: reusable-analysis and fallback helper behavior.
- `README.md`, `README_ZH.md`, `docs/DEVELOPMENT.md`: PaperPilot 2.0 documentation.

### Task 1: Deterministic Templates, Scaffold, and Inspector

**Files:**
- Create: `productize/__init__.py`
- Create: `productize/product_templates.py`
- Create: `productize/product_scaffold.py`
- Create: `productize/product_tester.py`
- Create: `tests/test_product_templates.py`
- Create: `tests/test_product_scaffold.py`

- [ ] **Step 1: Write failing template tests**

Create tests that import `select_product_template()` and assert:

```python
self.assertEqual(select_product_template("", "", "", "", "image"), "image")
self.assertEqual(select_product_template("", "image segmentation", "", ""), "image")
self.assertEqual(select_product_template("", "question answering", "", ""), "text")
self.assertEqual(select_product_template("", "object tracking video", "", ""), "video")
self.assertEqual(select_product_template("", "unknown method", "", ""), "file")
```

- [ ] **Step 2: Verify template tests fail**

Run:

```bash
python -m unittest tests.test_product_templates -v
```

Expected: import failure because `productize.product_templates` does not exist.

- [ ] **Step 3: Implement template selection and source builders**

Implement explicit preference normalization for `auto/image/text/video/file`,
keyword scoring with deterministic priority, a `file` fallback,
`build_app_source(template_type)`, and `build_adapter_source(template_type,
repo_path)`. Generated adapters must expose `ModelAdapter.setup()`,
`load_model()`, and `predict()` and return the exact approved mock payload for
each template. Generated apps must render the matching Streamlit input,
instantiate `ModelAdapter(mock_mode=True)`, display JSON, and offer a JSON
download.

- [ ] **Step 4: Verify template tests pass**

Run:

```bash
python -m unittest tests.test_product_templates -v
```

Expected: all template tests pass.

- [ ] **Step 5: Write failing scaffold and inspector tests**

Tests must use `TemporaryDirectory()` and assert that `scaffold_product()`:

```python
required = {
    "app.py",
    "adapter.py",
    "README.md",
    "product_spec.md",
    "requirements.txt",
    "outputs",
}
self.assertEqual({path.name for path in root.iterdir()}, required)
self.assertTrue(result["success"])
```

For each template, dynamically import the generated adapter, call
`setup()`, `load_model()`, and `predict()`, and assert its returned `type`.
Create an existing output directory with a marker and assert a sibling
`generated_product_backup_*` retains it. Assert
`inspect_generated_product()` reports complete files, successful compilation,
mock mode, and README run instructions. Also test a missing file and invalid
Python source.

- [ ] **Step 6: Verify scaffold tests fail**

Run:

```bash
python -m unittest tests.test_product_scaffold -v
```

Expected: import failure because scaffold and inspector functions do not exist.

- [ ] **Step 7: Implement scaffold and inspector**

Use `Path`, `shutil.move`, and a UTC timestamp with microseconds for collision
resistance. Write UTF-8 text, create `outputs/`, and return `output_dir`,
`files`, `backup_dir`, `success`, and `message`. The generated README must
contain `pip install -r requirements.txt`, `streamlit run app.py`, mock-mode
behavior, real integration guidance, and limitations. Use `py_compile.compile`
with `doraise=True` in the inspector and return `exists`, `missing_files`,
`files`, `can_run_mock`, `readme_has_run_command`, `syntax_ok`,
`compile_errors`, and `notes`.

- [ ] **Step 8: Run deterministic module tests and regression suite**

Run:

```bash
python -m unittest tests.test_product_templates tests.test_product_scaffold -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit deterministic generation**

```bash
git add productize tests/test_product_templates.py tests/test_product_scaffold.py
git commit -m "feat(productize): add product template scaffolding"
```

### Task 2: Productize Agents and Prompts

**Files:**
- Create: `agents/product_opportunity_agent.py`
- Create: `agents/product_designer_agent.py`
- Create: `agents/tech_adapter_agent.py`
- Create: `agents/frontend_builder_agent.py`
- Create: `agents/product_test_agent.py`
- Create: `prompts/product_opportunity_prompt.txt`
- Create: `prompts/product_designer_prompt.txt`
- Create: `prompts/tech_adapter_prompt.txt`
- Create: `prompts/frontend_builder_prompt.txt`
- Create: `prompts/product_test_prompt.txt`
- Modify: `agents/__init__.py`
- Create: `tests/test_product_agents.py`

- [ ] **Step 1: Write failing agent tests**

Instantiate all five agents with `LLMClient(mock_mode=True)`, assert their
prompt files load non-empty content, call `run()` with each documented input
dictionary, and assert a non-empty string containing `PaperPilot Mock Result`.
Assert each class is importable from `agents`.

- [ ] **Step 2: Verify agent tests fail**

Run:

```bash
python -m unittest tests.test_product_agents -v
```

Expected: import failures for the five new agents.

- [ ] **Step 3: Add approved prompts and BaseAgent wrappers**

Each wrapper must only configure a descriptive agent name, its prompt filename,
and the supplied `LLMClient`. Copy the five prompt bodies from
`docs/PaperPilot_Productize_Codex_Prompt.md` without changing their safety
constraints. Export all five classes from `agents/__init__.py`.

- [ ] **Step 4: Verify agents and existing suite**

Run:

```bash
python -m unittest tests.test_product_agents -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit agents**

```bash
git add agents prompts tests/test_product_agents.py
git commit -m "feat(agent): add productize agents"
```

### Task 3: Resilient Productize Pipeline

**Files:**
- Create: `productize/product_pipeline.py`
- Modify: `productize/__init__.py`
- Create: `tests/test_product_pipeline.py`

- [ ] **Step 1: Write failing complete-pipeline test**

Run `run_productize_pipeline()` with non-empty analysis strings,
`LLMClient(mock_mode=True)`, `preferred_type="text"`, and a temporary output
directory. Assert all documented result keys exist, template type is `text`,
the scaffold succeeds, inspection succeeds, and generated files exist.

- [ ] **Step 2: Write failing degraded-pipeline test**

Patch `ProductOpportunityAgent.run` to raise an exception and assert the result
records an error while still producing a valid mock scaffold and deterministic
fallback product specification.

- [ ] **Step 3: Verify pipeline tests fail**

Run:

```bash
python -m unittest tests.test_product_pipeline -v
```

Expected: import failure because `productize.product_pipeline` does not exist.

- [ ] **Step 4: Implement isolated stage execution**

Initialize every documented output key plus `inspection` and `errors`. Add a
private runner that catches initialization, exceptions, empty strings, and
existing BaseAgent failure markers. Run opportunity, design, template
selection, adapter, frontend, scaffold, inspection, and test-report stages in
order. If design output is absent, create a complete deterministic Markdown
spec describing a mock-first file-analysis prototype. Always pass deterministic
inspection data to Product Test Agent.

- [ ] **Step 5: Verify pipeline and regression tests**

Run:

```bash
python -m unittest tests.test_product_pipeline -v
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit pipeline**

```bash
git add productize/product_pipeline.py productize/__init__.py tests/test_product_pipeline.py
git commit -m "feat(productize): orchestrate product generation"
```

### Task 4: Streamlit Mode Integration and Automatic Analysis

**Files:**
- Modify: `app.py`
- Create: `tests/test_productize_ui.py`

- [ ] **Step 1: Write failing UI helper tests**

Add tests for `_has_productize_context(result)` returning true only when
`paper_info`, `method_info`, `repo_info`, and `repo_path` are non-empty. Add a
test for `_run_analysis_for_productize(...)` that patches `run_paperpilot`,
passes saved PDF and form values, and asserts the existing pipeline receives
the configured LLM client and a reproduction goal that includes repository
analysis.

- [ ] **Step 2: Verify UI tests fail**

Run:

```bash
python -m unittest tests.test_productize_ui -v
```

Expected: attribute failures for the new helpers.

- [ ] **Step 3: Implement mode-specific render functions**

Extract the current page body into `_render_reproduce_mode()` without changing
its labels, session keys, Runner, Debug, downloads, or behavior. Add sidebar
radio options `Reproduce Paper` and `Productize Paper`. Add
`_render_productize_mode()` with shared PDF, repository, hardware inputs plus
target user, product goal, and preferred type.

On generation, reuse session analysis when `_has_productize_context()` is true.
Otherwise save the uploaded PDF and call `run_paperpilot()` with
`goal="run official demo"` so paper, method, and repository analysis are
available without planning training. Store that result under
`paperpilot_result`, validate context, then call `run_productize_pipeline()`.

Display all Productize outputs, generated file contents in tabs, errors,
inspection details, and the run command. Do not launch generated Streamlit
automatically.

- [ ] **Step 4: Verify UI tests and app import**

Run:

```bash
python -m unittest tests.test_productize_ui -v
python -m py_compile app.py
python -c "import app; print('app import ok')"
python -m unittest discover -s tests -v
```

Expected: all commands exit successfully.

- [ ] **Step 5: Commit UI integration**

```bash
git add app.py tests/test_productize_ui.py
git commit -m "feat(ui): add productize mode"
```

### Task 5: PaperPilot 2.0 Documentation

**Files:**
- Modify: `README.md`
- Modify: `README_ZH.md`
- Modify: `docs/DEVELOPMENT.md`

- [ ] **Step 1: Update English documentation**

Describe PaperPilot 2.0 as a reproduction and limited product-prototyping
assistant. Document both modes, automatic analysis fallback, four templates,
generated files, mock-first adapter behavior, backup behavior, demo workflow,
run commands, safety constraints, and limitations.

- [ ] **Step 2: Update Chinese documentation**

Mirror the English content and include the required Chinese PaperPilot 2.0
positioning paragraph from the product requirements.

- [ ] **Step 3: Update development rules**

Add `productize` as a Conventional Commit scope, add the package and generated
product to the architecture overview, and document that generated adapters
remain mock-first and never execute source repositories automatically.

- [ ] **Step 4: Verify documentation**

Run:

```bash
rg -n "Productize Mode|generated_product|streamlit run app.py|mock mode" README.md
rg -n "产品化模式|generated_product|streamlit run app.py|mock mode" README_ZH.md
rg -n "productize|generated_product" docs/DEVELOPMENT.md
git diff --check
```

Expected: every search finds the documented behavior and diff check succeeds.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md README_ZH.md docs/DEVELOPMENT.md
git commit -m "docs(readme): document productize mode"
```

### Task 6: Final Verification, Review, and GitHub Publication

**Files:**
- Modify only files required by review findings.

- [ ] **Step 1: Run complete automated verification**

```bash
python -m unittest discover -s tests -v
python -m compileall -q agents productize tools main.py app.py
git diff --check master...HEAD
```

Expected: zero test failures, zero compile errors, and no whitespace errors.

- [ ] **Step 2: Run a full mock product smoke test**

Create a temporary PDF with PyMuPDF, patch repository acquisition to a
temporary local repository, run `run_paperpilot()`, feed its analysis to
`run_productize_pipeline()`, import the generated adapter, and assert
`predict()` returns the selected template type. Use a temporary generated
product directory so tracked files are unaffected.

- [ ] **Step 3: Run Streamlit headless startup smoke check**

```bash
timeout 15s streamlit run app.py --server.headless true --server.port 8765
```

Expected: logs contain the local URL and no traceback before timeout terminates
the server.

- [ ] **Step 4: Review the complete branch**

Compare `master...HEAD` against
`docs/implementation-plan/2026-06-10-productize-mode-design.md` and the product
requirements. Fix every critical or important finding, add regression tests
first for behavioral corrections, and rerun Steps 1-3.

- [ ] **Step 5: Confirm publication prerequisites**

```bash
git status --short --branch
git log --oneline master..HEAD
gh auth status
```

Expected: intended branch only, conventional commits present, and GitHub CLI
authenticated.

- [ ] **Step 6: Push and open a draft pull request**

```bash
git push -u origin codex/productize-mode
gh pr create --draft --base master --head codex/productize-mode --title "[codex] add Productize Mode" --body-file /tmp/paperpilot-productize-pr.md
```

The PR body must summarize architecture, generated product behavior, automatic
analysis fallback, security constraints, documentation, and exact verification
commands.
