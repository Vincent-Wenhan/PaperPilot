# Generation Protocol Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured generation protocols for Reproduce and Productize, then surface those protocols in generated artifacts and host UI summaries.

**Architecture:** Add Pydantic protocol schemas and deterministic builders before existing generation steps. Reproduce code generation receives an `ImplementationBlueprint`; Productize scaffold receives a `ProductUISpec`; host UI helpers render concise summaries from the new result keys while preserving existing raw/debug views.

**Tech Stack:** Python 3.12, Pydantic, LangGraph state dictionaries, Streamlit, pytest/unittest-compatible tests.

---

## File Structure

- Modify `schemas/reproduction_schema.py`: add `BlueprintFile` and `ImplementationBlueprint`.
- Create `tools/implementation_blueprint.py`: deterministic blueprint builder and blueprint coverage assessor.
- Modify `tools/code_quality.py`: merge blueprint coverage into generated-code quality output.
- Modify `pipeline/reproduce_pipeline.py`: build blueprint, pass it to the implementation agent, store `implementation_blueprint` and `blueprint_quality`.
- Modify `prompts/reproduction_implementation_prompt.txt`: instruct the implementation agent to follow the blueprint.
- Modify `schemas/product_schema.py`: add `UIControl`, `ResultComponent`, `UIStateCopy`, `ProductUISpec`.
- Create `productize/ui_spec.py`: deterministic UI spec builder from `ProductPlan` and `PrototypePlan`.
- Modify `productize/product_templates.py`: render app source from `ProductUISpec` when available.
- Modify `productize/product_scaffold.py`: accept optional `ui_spec`.
- Modify `productize/product_tester.py`: inspect UI spec coverage markers.
- Modify `pipeline/productize_pipeline.py`: build and store `ui_spec`, pass it to scaffold.
- Modify `ui/shared.py`: add generated project workbench summary helpers and render blueprint details.
- Modify `ui/productize_helpers.py`: add product prototype workbench summary helpers and render UI spec details.
- Update docs: `README.md`, `README_ZH.md`, `docs/DEVELOPMENT.md`, and `docs/implementation-plan/2026-06-18-generation-protocol-workbench.md`.

---

### Task 1: Reproduce Blueprint Schema and Builder

**Files:**
- Modify: `schemas/reproduction_schema.py`
- Create: `tools/implementation_blueprint.py`
- Test: `tests/test_implementation_blueprint.py`

- [ ] **Step 1: Write failing blueprint builder tests**

Create `tests/test_implementation_blueprint.py`:

```python
from __future__ import annotations

import unittest

from schemas.reproduction_schema import (
    MethodModule,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
)
from tools.implementation_blueprint import (
    assess_blueprint_coverage,
    build_implementation_blueprint,
)
from schemas.reproduction_schema import GeneratedCodeFile, ImplementationBundle


class ImplementationBlueprintTests(unittest.TestCase):
    def test_builds_multi_file_blueprint_from_method_modules(self) -> None:
        paper = PaperUnderstanding(
            title="Contrastive Graph Learner",
            method_modules=[
                MethodModule(
                    name="Graph Encoder",
                    purpose="Encode graph neighborhoods",
                    inputs=["node features"],
                    outputs=["node embeddings"],
                ),
                MethodModule(
                    name="Contrastive Objective",
                    purpose="Score positive and negative pairs",
                    inputs=["node embeddings"],
                    outputs=["loss"],
                ),
            ],
            end_to_end_dataflow=[
                "Load synthetic graph features",
                "Encode neighborhoods",
                "Compute contrastive score",
            ],
        )
        repository = RepositoryUnderstanding(detected_framework="pytorch")
        plan = ReproductionPlan(
            implementation_strategy="Implement a tiny synthetic graph dataflow."
        )

        blueprint = build_implementation_blueprint(
            paper,
            repository,
            plan,
            hardware="CPU only",
            goal="minimal training experiment",
        )

        paths = [item.path for item in blueprint.files]
        self.assertIn("README.md", paths)
        self.assertIn("config.py", paths)
        self.assertIn("main.py", paths)
        self.assertIn("tests/test_dataflow.py", paths)
        self.assertTrue(any(path.endswith(".py") and path not in {"main.py", "config.py"} for path in paths))
        self.assertIn("python main.py --smoke-test", blueprint.required_entrypoints)
        self.assertGreaterEqual(len(blueprint.core_dataflow), 3)

    def test_sparse_inputs_still_build_conservative_blueprint(self) -> None:
        blueprint = build_implementation_blueprint(
            PaperUnderstanding(title=""),
            RepositoryUnderstanding(),
            ReproductionPlan(),
            hardware="CPU only",
            goal="run official demo",
        )

        self.assertEqual(blueprint.project_name, "paperpilot_reproduction")
        self.assertTrue(blueprint.files)
        self.assertTrue(blueprint.quality_requirements)
        self.assertTrue(blueprint.forbidden_patterns)

    def test_coverage_flags_missing_planned_file_and_symbol(self) -> None:
        blueprint = build_implementation_blueprint(
            PaperUnderstanding(
                method_modules=[MethodModule(name="Encoder", purpose="Encode inputs")]
            ),
            RepositoryUnderstanding(),
            ReproductionPlan(),
            hardware="CPU only",
            goal="minimal training experiment",
        )
        bundle = ImplementationBundle(
            files=[
                GeneratedCodeFile(
                    path="main.py",
                    purpose="entry",
                    content="def main() -> None:\n    print('ok')\n",
                )
            ]
        )

        coverage = assess_blueprint_coverage(bundle, blueprint)

        self.assertFalse(coverage["passes_blueprint_coverage"])
        self.assertIn("missing_blueprint_files", coverage["issue_codes"])
        self.assertTrue(coverage["issues"])
        self.assertTrue(coverage["suggestions"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_implementation_blueprint.py -q
```

Expected: FAIL during import because `tools.implementation_blueprint` and the new schema classes do not exist.

- [ ] **Step 3: Add blueprint schema classes**

Modify `schemas/reproduction_schema.py` after `GeneratedCodeFile`:

```python
class BlueprintFile(BaseModel):
    path: str = ""
    responsibility: str = ""
    required_symbols: list[str] = Field(default_factory=list)
    test_relevance: str = ""


class ImplementationBlueprint(BaseModel):
    project_name: str = "paperpilot_reproduction"
    objective: str = ""
    architecture_summary: str = ""
    files: list[BlueprintFile] = Field(default_factory=list)
    core_dataflow: list[str] = Field(default_factory=list)
    required_entrypoints: list[str] = Field(default_factory=list)
    quality_requirements: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Implement the deterministic blueprint builder**

Create `tools/implementation_blueprint.py`:

```python
"""Deterministic implementation blueprints for generated reproductions."""

from __future__ import annotations

import re
from typing import Any

from schemas.reproduction_schema import (
    BlueprintFile,
    ImplementationBlueprint,
    ImplementationBundle,
    PaperUnderstanding,
    RepositoryUnderstanding,
    ReproductionPlan,
)


def _safe_name(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_ -]+", "", value).strip().lower()
    cleaned = re.sub(r"[\s-]+", "_", cleaned)
    return cleaned[:64].strip("_") or fallback


def _module_path(module_name: str, index: int) -> str:
    stem = _safe_name(module_name, f"method_module_{index}")
    if stem in {"main", "config", "tests", "test_dataflow"}:
        stem = f"{stem}_module"
    return f"{stem}.py"


def build_implementation_blueprint(
    paper: PaperUnderstanding,
    repository: RepositoryUnderstanding,
    plan: ReproductionPlan,
    *,
    hardware: str,
    goal: str,
) -> ImplementationBlueprint:
    """Build a conservative file architecture for generated reproduction code."""
    project_name = _safe_name(paper.title, "paperpilot_reproduction")
    method_files: list[BlueprintFile] = []
    for index, module in enumerate(paper.method_modules[:3], 1):
        symbol = _safe_name(module.name, f"method_module_{index}")
        method_files.append(
            BlueprintFile(
                path=_module_path(module.name, index),
                responsibility=module.purpose or f"Implement {module.name or symbol}.",
                required_symbols=[symbol],
                test_relevance="Covered by tests/test_dataflow.py synthetic smoke test.",
            )
        )
    if not method_files:
        method_files.append(
            BlueprintFile(
                path="model.py",
                responsibility="Implement the central paper method approximation.",
                required_symbols=["run_model"],
                test_relevance="Covered by tests/test_dataflow.py synthetic smoke test.",
            )
        )

    files = [
        BlueprintFile(
            path="README.md",
            responsibility="Document scope, assumptions, evidence, and validation commands.",
            required_symbols=[],
            test_relevance="Documents how to inspect generated code.",
        ),
        BlueprintFile(
            path="config.py",
            responsibility="Store typed configuration for the synthetic run.",
            required_symbols=["ModelConfig"],
            test_relevance="Imported by method modules and tests.",
        ),
        *method_files,
        BlueprintFile(
            path="main.py",
            responsibility="Provide a safe CLI with --smoke-test.",
            required_symbols=["main"],
            test_relevance="Smoke command entry point.",
        ),
        BlueprintFile(
            path="tests/test_dataflow.py",
            responsibility="Verify the synthetic dataflow executes end to end.",
            required_symbols=["test_synthetic_dataflow"],
            test_relevance="Primary regression test for generated code.",
        ),
        BlueprintFile(
            path="requirements.txt",
            responsibility="Declare minimal dependencies.",
            required_symbols=[],
            test_relevance="Dependency review artifact.",
        ),
    ]
    dataflow = paper.end_to_end_dataflow or [
        "Create tiny synthetic input",
        "Run the generated method approximation",
        "Check output shape or score",
    ]
    return ImplementationBlueprint(
        project_name=project_name,
        objective=plan.implementation_strategy
        or f"Generate a bounded {goal} reproduction for {hardware}.",
        architecture_summary=(
            "A small inspectable Python project with configuration, method modules, "
            "a safe CLI, and a synthetic dataflow test."
        ),
        files=files,
        core_dataflow=dataflow[:6],
        required_entrypoints=["python main.py --smoke-test"],
        quality_requirements=[
            "All planned Python files are present.",
            "Required symbols are implemented.",
            "A synthetic dataflow test is present under tests/.",
            "README.md documents scope and validation.",
        ],
        forbidden_patterns=[
            "pass",
            "raise NotImplementedError",
            "ellipsis expression",
            "shell=True",
            "network download during import or --help",
        ],
    )


def assess_blueprint_coverage(
    bundle: ImplementationBundle,
    blueprint: ImplementationBlueprint,
) -> dict[str, Any]:
    """Compare generated files and source text against the expected blueprint."""
    generated = {
        item.path.strip().replace("\\", "/").lower(): item.content
        for item in bundle.files
        if item.path.strip()
    }
    planned = {
        item.path.strip().replace("\\", "/").lower(): item
        for item in blueprint.files
        if item.path.strip()
    }
    issue_codes: list[str] = []
    issues: list[str] = []
    suggestions: list[str] = []

    missing_files = [path for path in planned if path not in generated]
    if missing_files:
        issue_codes.append("missing_blueprint_files")
        issues.append("Generated bundle is missing planned files: " + ", ".join(missing_files))
        suggestions.append("Generate every file listed in implementation_blueprint.files.")

    missing_symbols: list[str] = []
    for path, planned_file in planned.items():
        content = generated.get(path, "")
        for symbol in planned_file.required_symbols:
            if symbol and symbol not in content:
                missing_symbols.append(f"{path}:{symbol}")
    if missing_symbols:
        issue_codes.append("missing_required_symbols")
        issues.append("Generated files are missing required symbols: " + ", ".join(missing_symbols))
        suggestions.append("Implement the required classes, functions, or tests named by the blueprint.")

    expected_smoke = blueprint.required_entrypoints[0] if blueprint.required_entrypoints else ""
    if expected_smoke and bundle.smoke_test_command.strip() != expected_smoke:
        issue_codes.append("smoke_command_mismatch")
        issues.append(f"Smoke-test command should be `{expected_smoke}`.")
        suggestions.append("Set smoke_test_command to the blueprint entrypoint.")

    return {
        "passes_blueprint_coverage": not issue_codes,
        "issue_codes": issue_codes,
        "issues": issues,
        "suggestions": suggestions,
        "metrics": {
            "planned_files": len(planned),
            "generated_files": len(generated),
            "missing_files": len(missing_files),
            "missing_symbols": len(missing_symbols),
        },
    }
```

- [ ] **Step 5: Run the blueprint tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_implementation_blueprint.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

Run:

```bash
git add schemas/reproduction_schema.py tools/implementation_blueprint.py tests/test_implementation_blueprint.py
git commit -m "feat(reproduce): add implementation blueprint builder"
```

---

### Task 2: Reproduce Pipeline Blueprint Integration

**Files:**
- Modify: `pipeline/reproduce_pipeline.py`
- Modify: `tools/code_quality.py`
- Modify: `prompts/reproduction_implementation_prompt.txt`
- Test: `tests/test_code_quality.py`
- Test: `tests/test_e2e_pipeline.py`

- [ ] **Step 1: Write failing quality coverage test**

Append to `tests/test_code_quality.py`:

```python
    def test_quality_merges_blueprint_coverage_failures(self) -> None:
        from schemas.reproduction_schema import BlueprintFile, ImplementationBlueprint

        blueprint = ImplementationBlueprint(
            files=[
                BlueprintFile(
                    path="model.py",
                    responsibility="method",
                    required_symbols=["run_model"],
                ),
                BlueprintFile(
                    path="tests/test_dataflow.py",
                    responsibility="test",
                    required_symbols=["test_synthetic_dataflow"],
                ),
            ],
            required_entrypoints=["python main.py --smoke-test"],
        )
        bundle = ImplementationBundle(
            smoke_test_command="python main.py --smoke-test",
            files=[
                GeneratedCodeFile(
                    path="main.py",
                    purpose="entry",
                    content="def main() -> None:\n    print('ok')\n",
                )
            ],
        )

        quality = assess_implementation_quality(bundle, blueprint=blueprint)

        self.assertFalse(quality["passes_minimum_quality"])
        self.assertIn("missing_blueprint_files", quality["issue_codes"])
        self.assertIn("blueprint", quality["metrics"])
```

- [ ] **Step 2: Write failing pipeline result test**

Add to `tests/test_e2e_pipeline.py` or the nearest existing pipeline test file that already calls `run_paperpilot()` with mock mode:

```python
def test_mock_reproduce_result_includes_implementation_blueprint(tmp_path):
    import fitz
    from main import run_paperpilot
    from tools.llm_client import LLMClient

    pdf = tmp_path / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "A paper describing an encoder and a contrastive objective.")
    doc.save(pdf)
    doc.close()

    result = run_paperpilot(
        pdf_path=str(pdf),
        github_url="",
        hardware="CPU only",
        gpu_info="",
        goal="minimal training experiment",
        llm_client=LLMClient(mock_mode=True),
        generate_code=True,
        paper_name="blueprint_test",
    )

    assert result["implementation_blueprint"]["files"]
    assert "blueprint_quality" in result
    assert result["code_quality"]["metrics"]["blueprint"]["planned_files"] > 0
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_code_quality.py tests/test_e2e_pipeline.py -q
```

Expected: FAIL because `assess_implementation_quality()` does not accept `blueprint`, and pipeline result lacks blueprint keys.

- [ ] **Step 4: Extend code quality with blueprint coverage**

Modify `tools/code_quality.py` with these concrete changes:

```python
from schemas.reproduction_schema import ImplementationBlueprint, ImplementationBundle
from tools.implementation_blueprint import assess_blueprint_coverage


def assess_implementation_quality(
    bundle: ImplementationBundle,
    blueprint: ImplementationBlueprint | None = None,
) -> dict[str, Any]:
    paths = _normalized_paths(bundle)
    python_files = [
        item for item in bundle.files if item.path.strip().lower().endswith(".py")
    ]
    tests = [
        path
        for path in paths
        if path.startswith("tests/") and path.endswith(".py")
    ]
    blueprint_quality = (
        assess_blueprint_coverage(bundle, blueprint)
        if blueprint is not None
        else {
            "passes_blueprint_coverage": True,
            "issue_codes": [],
            "issues": [],
            "suggestions": [],
            "metrics": {},
        }
    )
    issue_codes.extend(code for code in blueprint_quality["issue_codes"] if code not in issue_codes)
    issues.extend(str(item) for item in blueprint_quality["issues"] if item not in issues)
    suggestions.extend(str(item) for item in blueprint_quality["suggestions"] if item not in suggestions)
    has_readme = "readme.md" in paths
    has_config = any(path in {"config.py", "settings.py"} for path in paths)
    has_entrypoint = any(path in {"main.py", "app.py", "run.py"} for path in paths)
    has_requirements = "requirements.txt" in paths
    return {
        "overall_score": overall_score,
        "passes_minimum_quality": (
            overall_score >= 3.5
            and not {"place" + "holder_body", "missing_python", "missing_tests"}.intersection(issue_codes)
            and blueprint_quality["passes_blueprint_coverage"]
        ),
        "metrics": {
            "files": len(paths),
            "python_files": len(python_files),
            "has_tests": bool(tests),
            "has_readme": has_readme,
            "has_config": has_config,
            "has_entrypoint": has_entrypoint,
            "has_requirements": has_requirements,
            "functions": complexity["functions"],
            "classes": complexity["classes"],
            "blueprint": blueprint_quality["metrics"],
        },
    }
```

Keep the existing metrics intact and add only the nested `blueprint` key.

- [ ] **Step 5: Build and pass blueprint in Reproduce pipeline**

Modify `pipeline/reproduce_pipeline.py` imports:

```python
from tools.implementation_blueprint import build_implementation_blueprint
```

Add initial result keys:

```python
"implementation_blueprint": {},
"blueprint_quality": {},
```

Inside `generate_implementation()`, before `implementation_input`:

```python
blueprint = build_implementation_blueprint(
    PaperUnderstanding.model_validate(state.get("research_understanding") or {}),
    RepositoryUnderstanding.model_validate(state.get("repository_understanding") or {}),
    ReproductionPlan.model_validate(state.get("reproduction_plan") or {}),
    hardware=hardware,
    goal=goal,
)
result["implementation_blueprint"] = blueprint.model_dump(mode="json")
```

Add to `implementation_input`:

```python
"implementation_blueprint": result["implementation_blueprint"],
```

Update quality assessment calls in both `generate_implementation()` and `revise_code()`:

```python
result["code_quality"] = assess_implementation_quality(implementation, blueprint=blueprint)
result["blueprint_quality"] = result["code_quality"]["metrics"].get("blueprint", {})
```

In `revise_code()`, reconstruct `blueprint` from `result["implementation_blueprint"]`.

- [ ] **Step 6: Update implementation prompt**

Modify `prompts/reproduction_implementation_prompt.txt` near the Method Specification section:

```text
## Implementation Blueprint
{implementation_blueprint}

Follow this blueprint as the project contract. Generate every planned file,
implement every required symbol, use the listed smoke-test entrypoint, and
explain any evidence-driven deviation in `assumptions`.
```

- [ ] **Step 7: Run focused tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_code_quality.py tests/test_e2e_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 2**

Run:

```bash
git add pipeline/reproduce_pipeline.py tools/code_quality.py prompts/reproduction_implementation_prompt.txt tests/test_code_quality.py tests/test_e2e_pipeline.py
git commit -m "feat(reproduce): enforce blueprint coverage"
```

---

### Task 3: Product UI Spec Schema and Builder

**Files:**
- Modify: `schemas/product_schema.py`
- Create: `productize/ui_spec.py`
- Test: `tests/test_product_ui_spec.py`

- [ ] **Step 1: Write failing UI spec tests**

Create `tests/test_product_ui_spec.py`:

```python
from __future__ import annotations

import unittest

from productize.ui_spec import build_product_ui_spec
from schemas.product_schema import PRD, ProductPlan, PrototypePlan


class ProductUISpecTests(unittest.TestCase):
    def test_builds_typed_controls_and_result_components(self) -> None:
        plan = ProductPlan(
            jtbd="Help instructors triage student answers.",
            selected_product="Misconception Triage",
            selection_reason="High classroom value.",
            prd=PRD(
                product_name="Misconception Triage",
                problem_statement="Teachers need fast evidence review.",
                core_features=["Rank weak concepts", "Export intervention checklist"],
                target_users=["Teachers"],
            ),
        )
        prototype = PrototypePlan(
            template_type="file",
            page_structure=["Upload answers", "Review ranked evidence"],
            user_inputs=["Course module selector", "Misconception sensitivity threshold"],
            system_outputs=["Ranked misconception summary", "Teacher intervention checklist"],
            mock_result={"confidence": 0.82, "next_action": "Assign mini lesson"},
            adapter_boundary=["preprocess answers", "postprocess evidence"],
        )

        spec = build_product_ui_spec(plan, prototype)

        self.assertEqual(spec.product_name, "Misconception Triage")
        self.assertTrue(any(control.control_type == "selectbox" for control in spec.input_controls))
        self.assertTrue(any(control.control_type == "slider" for control in spec.input_controls))
        self.assertTrue(any(component.component_type == "metric" for component in spec.result_components))
        self.assertIn("empty", spec.states.model_dump())

    def test_sparse_prototype_gets_conservative_spec(self) -> None:
        plan = ProductPlan(
            jtbd="Explore a paper capability.",
            selected_product="Paper Demo",
            selection_reason="Default mock-first product.",
            prd=PRD(product_name="Paper Demo", problem_statement="Need a demo."),
        )
        spec = build_product_ui_spec(plan, PrototypePlan(template_type="text"))

        self.assertEqual(spec.template_type, "text")
        self.assertGreaterEqual(len(spec.page_sections), 4)
        self.assertTrue(spec.input_controls)
        self.assertTrue(spec.result_components)
        self.assertTrue(spec.visual_rules)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing UI spec tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_product_ui_spec.py -q
```

Expected: FAIL because `productize.ui_spec` and UI spec schemas do not exist.

- [ ] **Step 3: Add Product UI schema classes**

Modify `schemas/product_schema.py` after `PrototypePlan`:

```python
class UIControl(BaseModel):
    control_id: str = ""
    label: str = ""
    control_type: str = "text_input"
    default: object | None = None
    options: list[str] = Field(default_factory=list)
    help_text: str = ""
    required: bool = False


class ResultComponent(BaseModel):
    component_id: str = ""
    label: str = ""
    component_type: str = "summary"
    source_key: str = ""
    description: str = ""


class UIStateCopy(BaseModel):
    empty: str = "Provide an input to start the mock workflow."
    loading: str = "Running mock analysis."
    success: str = "Mock analysis completed."
    error: str = "The mock workflow could not complete."


class ProductUISpec(BaseModel):
    product_name: str = ""
    template_type: str = "file"
    layout_mode: str = "workflow_dashboard"
    page_sections: list[str] = Field(default_factory=list)
    input_controls: list[UIControl] = Field(default_factory=list)
    result_components: list[ResultComponent] = Field(default_factory=list)
    mock_result_schema: dict[str, str] = Field(default_factory=dict)
    states: UIStateCopy = Field(default_factory=UIStateCopy)
    visual_rules: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Implement UI spec builder**

Create `productize/ui_spec.py`:

```python
"""Build structured UI specs for generated Productize prototypes."""

from __future__ import annotations

import re

from schemas.product_schema import (
    ProductPlan,
    ProductUISpec,
    PrototypePlan,
    ResultComponent,
    UIControl,
    UIStateCopy,
)


def _slug(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return cleaned[:48] or fallback


def _control_for_label(label: str, index: int) -> UIControl:
    lowered = label.lower()
    control_id = _slug(label, f"control_{index}")
    if any(word in lowered for word in ("threshold", "confidence", "sensitivity", "score")):
        return UIControl(
            control_id=control_id,
            label=label,
            control_type="slider",
            default=0.65,
            help_text="Tune the mock decision threshold.",
        )
    if any(word in lowered for word in ("mode", "type", "selector", "category", "module")):
        return UIControl(
            control_id=control_id,
            label=label,
            control_type="selectbox",
            default="Default",
            options=["Default", "Focused", "Broad"],
            help_text="Choose the mock workflow mode.",
        )
    if any(word in lowered for word in ("context", "notes", "scenario", "description")):
        return UIControl(
            control_id=control_id,
            label=label,
            control_type="textarea",
            default="",
            help_text="Provide optional context for the mock workflow.",
        )
    return UIControl(
        control_id=control_id,
        label=label,
        control_type="text_input",
        default="",
        help_text="Optional product-specific input.",
    )


def build_product_ui_spec(
    product_plan: ProductPlan,
    prototype_plan: PrototypePlan,
) -> ProductUISpec:
    """Normalize ProductPlan and PrototypePlan into renderable UI structure."""
    product_name = product_plan.prd.product_name or product_plan.selected_product or "Generated Product"
    page_sections = prototype_plan.page_structure or [
        "Set up task",
        "Provide input",
        "Run mock analysis",
        "Review evidence and limitations",
        "Export result",
    ]
    input_labels = prototype_plan.user_inputs or [
        f"{prototype_plan.template_type} input",
        "Decision context",
    ]
    controls = [_control_for_label(label, index) for index, label in enumerate(input_labels[:6], 1)]
    mock_schema = {
        str(key): str(type(value).__name__)
        for key, value in (prototype_plan.mock_result or {"summary": "mock result"}).items()
    }
    result_components = [
        ResultComponent(
            component_id="mode",
            label="Mode",
            component_type="metric",
            source_key="type",
            description="Mock adapter output type.",
        )
    ]
    for index, output in enumerate(prototype_plan.system_outputs or ["Structured mock result", "Downloadable JSON"], 1):
        result_components.append(
            ResultComponent(
                component_id=_slug(output, f"result_{index}"),
                label=output,
                component_type="summary",
                source_key="result",
                description=output,
            )
        )
    return ProductUISpec(
        product_name=product_name,
        template_type=prototype_plan.template_type or "file",
        layout_mode="workflow_dashboard",
        page_sections=page_sections[:7],
        input_controls=controls,
        result_components=result_components[:8],
        mock_result_schema=mock_schema,
        states=UIStateCopy(
            empty=f"Provide input to start {product_name}.",
            loading="Running safe mock analysis.",
            success="Mock workflow completed.",
            error="Mock workflow failed before producing a result.",
        ),
        visual_rules=[
            "compact dashboard layout",
            "8px-or-less panel radius",
            "no marketing hero",
            "raw JSON is secondary to summary content",
        ],
    )
```

- [ ] **Step 5: Run UI spec tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_product_ui_spec.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
git add schemas/product_schema.py productize/ui_spec.py tests/test_product_ui_spec.py
git commit -m "feat(productize): add structured ui spec builder"
```

---

### Task 4: ProductUISpec Scaffold and Inspector Integration

**Files:**
- Modify: `productize/product_templates.py`
- Modify: `productize/product_scaffold.py`
- Modify: `productize/product_tester.py`
- Modify: `pipeline/productize_pipeline.py`
- Test: `tests/test_product_scaffold.py`
- Test: `tests/test_product_pipeline.py`

- [ ] **Step 1: Write failing scaffold UI spec test**

Append to `tests/test_product_scaffold.py`:

```python
    def test_scaffold_renders_structured_ui_spec(self) -> None:
        from schemas.product_schema import ProductUISpec, ResultComponent, UIControl, UIStateCopy

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            ui_spec = ProductUISpec(
                product_name="Evidence Console",
                template_type="text",
                page_sections=["Prepare case", "Run analysis", "Review evidence"],
                input_controls=[
                    UIControl(
                        control_id="review_mode",
                        label="Review mode",
                        control_type="selectbox",
                        options=["Default", "Strict"],
                        default="Default",
                    ),
                    UIControl(
                        control_id="confidence_threshold",
                        label="Confidence threshold",
                        control_type="slider",
                        default=0.7,
                    ),
                ],
                result_components=[
                    ResultComponent(
                        component_id="confidence",
                        label="Confidence",
                        component_type="metric",
                        source_key="confidence",
                    ),
                    ResultComponent(
                        component_id="evidence",
                        label="Evidence summary",
                        component_type="summary",
                        source_key="evidence",
                    ),
                ],
                mock_result_schema={"confidence": "float", "evidence": "list"},
                states=UIStateCopy(
                    empty="Paste evidence to start.",
                    loading="Reviewing evidence.",
                    success="Evidence review complete.",
                    error="Evidence review failed.",
                ),
            )

            scaffold_product(
                template_type="text",
                product_spec="# Product\n\n## Product Name\n\nEvidence Console",
                adapter_plan="# Adapter",
                frontend_plan="# Frontend",
                repo_path="../workspace",
                output_dir=output_dir,
                ui_spec=ui_spec.model_dump(mode="json"),
            )

            app_source = (output_dir / "app.py").read_text(encoding="utf-8")
            self.assertIn("Evidence Console", app_source)
            self.assertIn("Review mode", app_source)
            self.assertIn("Evidence summary", app_source)
            self.assertIn("Paste evidence to start.", app_source)
            inspection = inspect_generated_product(output_dir)
            self.assertTrue(inspection["ui_spec_coverage"]["structured_controls"])
            self.assertTrue(inspection["ui_spec_coverage"]["result_components"])
            self.assertTrue(inspection["ui_spec_coverage"]["state_copy"])
```

- [ ] **Step 2: Write failing product pipeline UI spec test**

Append to `tests/test_product_pipeline.py`:

```python
    def test_pipeline_result_includes_ui_spec_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "generated_product"
            result = run_productize_pipeline(
                paper_info="A text classification paper.",
                method_info="Classifier returns confidence and evidence.",
                repo_info="Repository has inference.py.",
                repo_path="/tmp/source-repository",
                target_user="Teachers",
                product_goal="Review student misconceptions",
                llm_client=LLMClient(mock_mode=True),
                preferred_type="text",
                output_dir=output_dir,
            )

            self.assertTrue(result["ui_spec"]["input_controls"])
            self.assertTrue(result["inspection"]["ui_spec_coverage"]["structured_controls"])
```

- [ ] **Step 3: Run failing scaffold and pipeline tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_product_scaffold.py tests/test_product_pipeline.py -q
```

Expected: FAIL because `ui_spec` is not accepted by scaffold and not present in pipeline result.

- [ ] **Step 4: Update product scaffold and templates**

Modify `productize/product_scaffold.py`:

```python
def scaffold_product(
    template_type: str,
    product_spec: str,
    adapter_plan: str,
    frontend_plan: str,
    repo_path: str,
    output_dir: str | Path = "generated_product",
    prototype_plan: dict[str, Any] | None = None,
    ui_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contents = {
        "app.py": build_app_source(
            template_type,
            product_spec,
            frontend_plan,
            prototype_plan=prototype_plan,
            ui_spec=ui_spec,
        ),
    }
```

Modify `productize/product_templates.py`:

- Import `ProductUISpec`.
- Add `ui_spec: dict[str, Any] | None = None` to `build_app_source()`.
- When `ui_spec` is present, validate it with `ProductUISpec.model_validate(ui_spec)`.
- Render constants:

```python
UI_SPEC = spec.model_dump(mode="json")
UI_SPEC_MARKERS = {
    "structured_controls": True,
    "result_components": True,
    "state_copy": True,
    "mock_schema": True,
}
```

- Render control blocks from `spec.input_controls`:

```python
if control.control_type == "slider":
    context_values[id] = st.slider(label, 0.0, 1.0, float(default or 0.5), 0.05)
elif control.control_type == "selectbox":
    context_values[id] = st.selectbox(label, options or ["Default"])
elif control.control_type == "textarea":
    context_values[id] = st.text_area(label, value=str(default or ""))
else:
    context_values[id] = st.text_input(label, value=str(default or ""))
```

- Render `spec.states.empty` before the run button.
- Render `spec.result_components` inside the Summary tab before `st.json(result)`.

- [ ] **Step 5: Update inspector**

Modify `productize/product_tester.py`:

```python
ui_spec_coverage = {
    "structured_controls": "UI_SPEC_MARKERS" in app_text and "structured_controls" in app_text,
    "result_components": "UI_SPEC_MARKERS" in app_text and "result_components" in app_text,
    "state_copy": "UI_SPEC_MARKERS" in app_text and "state_copy" in app_text,
    "mock_schema": "UI_SPEC_MARKERS" in app_text and "mock_schema" in app_text,
}
```

Return `ui_spec_coverage` in the inspection dictionary. Keep `has_rich_layout` for backward compatibility.

- [ ] **Step 6: Build UI spec in product pipeline**

Modify `pipeline/productize_pipeline.py`:

```python
from productize.ui_spec import build_product_ui_spec
```

Add `"ui_spec": {}` to `_new_product_result()`.

In `_invoke_execution_graph()` after `prototype` and before scaffold:

```python
ui_spec = build_product_ui_spec(plan, prototype)
```

Store it in `compatibility_result` and pass it to `scaffold_product(ui_spec=ui_spec.model_dump(mode="json"))`.

- [ ] **Step 7: Run focused Productize tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_product_ui_spec.py tests/test_product_scaffold.py tests/test_product_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 4**

Run:

```bash
git add productize/product_templates.py productize/product_scaffold.py productize/product_tester.py pipeline/productize_pipeline.py tests/test_product_scaffold.py tests/test_product_pipeline.py
git commit -m "feat(productize): render prototypes from ui spec"
```

---

### Task 5: Host UI Workbench Summaries

**Files:**
- Modify: `ui/shared.py`
- Modify: `ui/productize_helpers.py`
- Test: `tests/test_productize_ui.py`
- Test: `tests/test_reproduce_ui.py`

- [ ] **Step 1: Write failing Reproduce summary helper test**

Create `tests/test_reproduce_ui.py` if it does not exist:

```python
from __future__ import annotations

from ui.shared import summarize_generated_project


def test_summarize_generated_project_includes_blueprint_quality() -> None:
    result = {
        "generated_repo_path": "/tmp/generated",
        "implementation_model": "gpt-4.1",
        "generated_files": ["main.py", "model.py", "tests/test_dataflow.py"],
        "implementation_blueprint": {"files": [{"path": "main.py"}, {"path": "model.py"}]},
        "code_quality": {"overall_score": 4.2, "passes_minimum_quality": True},
        "blueprint_quality": {"planned_files": 2, "missing_files": 0},
        "implementation_bundle": {"smoke_test_command": "python main.py --smoke-test"},
    }

    summary = summarize_generated_project(result)

    assert summary["status"] == "ready"
    assert summary["blueprint_file_count"] == 2
    assert summary["generated_file_count"] == 3
    assert summary["quality_score"] == 4.2
    assert summary["smoke_test_command"] == "python main.py --smoke-test"
```

- [ ] **Step 2: Write failing Productize summary test**

Append to `tests/test_productize_ui.py`:

```python
def test_summarize_generated_product_includes_ui_spec_coverage() -> None:
    from ui.productize_helpers import summarize_generated_product

    result = {
        "prd": {"product_name": "Evidence Console", "target_users": ["Teachers"]},
        "template_type": "text",
        "ui_spec": {"input_controls": [{"label": "Review mode"}]},
        "scaffold_result": {
            "success": True,
            "output_dir": "/tmp/generated_product",
            "files": ["app.py", "adapter.py"],
        },
        "inspection": {
            "syntax_ok": True,
            "can_run_mock": True,
            "has_rich_layout": True,
            "ui_spec_coverage": {
                "structured_controls": True,
                "result_components": True,
                "state_copy": True,
                "mock_schema": True,
            },
        },
    }

    summary = summarize_generated_product(result)

    assert summary["status"] == "ready"
    assert summary["product_name"] == "Evidence Console"
    assert summary["ui_spec_controls"] == 1
    assert summary["ui_spec_coverage"]["structured_controls"]
```

- [ ] **Step 3: Run failing UI helper tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_reproduce_ui.py tests/test_productize_ui.py -q
```

Expected: FAIL because `summarize_generated_project()` does not exist and product summary lacks UI spec fields.

- [ ] **Step 4: Implement Reproduce summary helper and render it**

Modify `ui/shared.py`:

```python
def summarize_generated_project(result: dict[str, Any]) -> dict[str, Any]:
    blueprint = result.get("implementation_blueprint") or {}
    quality = result.get("code_quality") or {}
    bundle = result.get("implementation_bundle") or {}
    generated_files = result.get("generated_files") or []
    passes = bool(quality.get("passes_minimum_quality"))
    return {
        "status": "ready" if passes and generated_files else "needs_review",
        "generated_repo_path": str(result.get("generated_repo_path") or ""),
        "implementation_model": str(result.get("implementation_model") or ""),
        "blueprint_file_count": len(blueprint.get("files") or []),
        "generated_file_count": len(generated_files),
        "quality_score": quality.get("overall_score", "n/a"),
        "blueprint_quality": result.get("blueprint_quality") or {},
        "smoke_test_command": bundle.get("smoke_test_command", ""),
    }
```

In `show_outputs()` under the Code / Repository tab before raw code expanders, render metrics from this summary and a "Blueprint" expander listing planned files.

- [ ] **Step 5: Extend Productize summary helper and render UI spec**

Modify `ui/productize_helpers.py` `summarize_generated_product()`:

```python
prd = result.get("prd") or {}
ui_spec = result.get("ui_spec") or {}
coverage = inspection.get("ui_spec_coverage") or {}
summary.update(
    {
        "product_name": prd.get("product_name", ""),
        "target_users": prd.get("target_users", []),
        "ui_spec_controls": len(ui_spec.get("input_controls") or []),
        "ui_spec_coverage": coverage,
    }
)
```

In `show_productize_result()`, add an "App Structure" tab that renders `ui_spec.page_sections`, `ui_spec.input_controls`, `ui_spec.result_components`, and `ui_spec.states` as markdown bullets before the raw JSON/debug sections.

- [ ] **Step 6: Run UI helper tests**

Run:

```bash
conda run -n paperpilot python -m pytest tests/test_reproduce_ui.py tests/test_productize_ui.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

Run:

```bash
git add ui/shared.py ui/productize_helpers.py tests/test_reproduce_ui.py tests/test_productize_ui.py
git commit -m "feat(ui): summarize generation protocols"
```

---

### Task 6: Documentation, Full Verification, and Publish

**Files:**
- Modify: `README.md`
- Modify: `README_ZH.md`
- Modify: `docs/DEVELOPMENT.md`
- Modify: `docs/implementation-plan/2026-06-18-generation-protocol-workbench.md`

- [ ] **Step 1: Update documentation**

Update `README.md` and `README_ZH.md` to mention:

- Reproduce Mode now creates an implementation blueprint before generated code.
- Generated code quality includes blueprint coverage.
- Productize Mode now creates a structured UI spec before scaffold.
- Productize result UI includes an App Structure view.

Update `docs/DEVELOPMENT.md` architecture overview to mention:

- `ImplementationBlueprint`
- `ProductUISpec`
- deterministic protocol builders

Update `docs/implementation-plan/2026-06-18-generation-protocol-workbench.md` with a short "Implemented Files" list after implementation.

- [ ] **Step 2: Run focused test suites**

Run:

```bash
conda run -n paperpilot python -m pytest \
  tests/test_implementation_blueprint.py \
  tests/test_code_quality.py \
  tests/test_e2e_pipeline.py \
  tests/test_product_ui_spec.py \
  tests/test_product_scaffold.py \
  tests/test_product_pipeline.py \
  tests/test_reproduce_ui.py \
  tests/test_productize_ui.py \
  -q
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```bash
conda run -n paperpilot python -m pytest -q
```

Expected: PASS with all tests passing.

- [ ] **Step 4: Inspect git diff**

Run:

```bash
git status --short --branch
git diff --stat
git diff --check
```

Expected: only planned files changed; `git diff --check` exits 0.

- [ ] **Step 5: Commit documentation**

Run:

```bash
git add README.md README_ZH.md docs/DEVELOPMENT.md docs/implementation-plan/2026-06-18-generation-protocol-workbench.md
git commit -m "docs(productize): document generation protocols"
```

- [ ] **Step 6: Push branch**

Run:

```bash
git push origin codex/product-quality-ui-upgrade
```

Expected: branch pushed successfully.

---

## Self-Review Checklist

- Spec coverage: Tasks 1-2 cover Reproduce blueprint protocol and quality integration; Tasks 3-4 cover ProductUISpec and scaffold inspection; Task 5 covers host UI workbench; Task 6 covers docs and verification.
- Red-flag scan: This plan avoids deferred-work markers and omitted code snippets.
- Type consistency: `ImplementationBlueprint`, `BlueprintFile`, `ProductUISpec`, `UIControl`, `ResultComponent`, and `UIStateCopy` names match across schema, builder, pipeline, and tests.
- Compatibility: Existing public result keys are preserved; new keys are additive; `scaffold_product()` keeps `prototype_plan` optional and adds `ui_spec` as optional.
