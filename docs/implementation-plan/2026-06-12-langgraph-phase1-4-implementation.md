# LangGraph Phase 1-4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce LangGraph orchestration, a safety-aware deterministic tool runtime, Productize fan-out/revision graphs, and a parallel Reproduce graph without breaking PaperPilot's public APIs.

**Architecture:** New `graphs/` and `runtime/` packages own orchestration and graph context. Existing agents, schemas, renderers, builders, and deterministic side effects are reused. `pipeline/` remains the compatibility boundary called by `app.py` and `main.py`.

**Tech Stack:** Python 3.12, LangGraph Graph API, Pydantic 2, Streamlit, PyYAML, pytest/unittest, existing PaperPilot agents and tools.

---

## Task 1: Dependencies, Graph State, Runtime Context, and Routing

**Files:**
- Modify: `requirements.txt`
- Create: `runtime/__init__.py`
- Create: `runtime/graph_state.py`
- Create: `runtime/collaboration.py`
- Create: `runtime/checkpointing.py`
- Create: `runtime/routing.py`
- Create: `tests/test_graph_runtime.py`

- [ ] **Step 1: Write failing runtime tests**

Test that:

```python
from runtime.graph_state import ProductizeState, ReproduceState
from runtime.routing import route_after_evaluation, route_command_plans
from runtime.checkpointing import build_checkpointer, build_graph_config

self.assertEqual(
    route_after_evaluation(
        {"evaluation": {"overall_score": 4.2}, "revision_count": 0, "max_revisions": 1}
    ),
    "finish",
)
self.assertEqual(
    route_after_evaluation(
        {
            "evaluation": {
                "overall_score": 2.5,
                "revision_suggestions": ["Improve adapter and prototype UI"],
            },
            "revision_count": 0,
            "max_revisions": 1,
        }
    ),
    "revise_prototype",
)
self.assertEqual(
    route_command_plans(
        [{"risk_level": "low"}, {"risk_level": "blocked"}]
    ),
    "blocked",
)
self.assertIsNone(build_checkpointer(False))
self.assertEqual(build_graph_config("thread-1"), {"configurable": {"thread_id": "thread-1"}})
```

Also assert `ProductizeState` and `ReproduceState` type hints contain reducer
channels for errors and tool logs, and collaboration `ReviewIssue` validates
severity and required fields.

- [ ] **Step 2: Verify runtime tests fail**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_graph_runtime -v
```

Expected: import failure because `runtime` does not exist.

- [ ] **Step 3: Add dependencies and runtime modules**

Add:

```text
langgraph>=0.2,<2
pyyaml>=6,<7
pytest>=8,<9
```

Implement TypedDict states with `Annotated[..., operator.add]`, context
dataclasses, `ReviewIssue`, in-memory checkpointer helpers, evaluation routing,
and command-plan routing. Missing evaluation scores route to revision until
the limit, then warnings. Any blocked command dominates review and safe routes.

- [ ] **Step 4: Verify runtime tests and imports**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_graph_runtime -v
conda run -n paperpilot python -c "import langgraph, yaml; print('graph dependencies ok')"
```

Expected: tests pass and imports succeed.

- [ ] **Step 5: Commit runtime foundation**

```bash
git add requirements.txt runtime tests/test_graph_runtime.py
git commit -m "feat(pipeline): add LangGraph runtime foundation"
```

## Task 2: Tool Schemas, Registry, Executor, and Safe Static Tools

**Files:**
- Create: `schemas/tool_schema.py`
- Modify: `schemas/__init__.py`
- Create: `runtime/tool_registry.py`
- Create: `runtime/tool_executor.py`
- Create: `tools/file_tools.py`
- Create: `tools/code_search_tools.py`
- Create: `tools/code_analysis_tools.py`
- Create: `tools/test_tools.py`
- Create: `tools/env_tools.py`
- Create: `tests/test_tool_runtime.py`
- Create: `tests/test_static_tools.py`

- [ ] **Step 1: Write failing registry and executor tests**

Tests must assert:

- duplicate tool names raise `ValueError`,
- unknown tools return failed `ToolResult`,
- unauthorized agents are rejected,
- blocked tools never execute,
- review tools require `allow_safety_levels={"review"}`,
- safe tools execute and record elapsed time,
- argument mismatch returns a normalized error instead of raising.

Use a local counter callable to prove rejected calls are not executed.

- [ ] **Step 2: Verify tool-runtime tests fail**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_tool_runtime -v
```

Expected: imports fail because tool runtime modules do not exist.

- [ ] **Step 3: Implement schemas, registry, and executor**

Implement Pydantic `ToolSpec`, `ToolCall`, and `ToolResult`, explicit
registration, authorization, safety-level checks, `inspect.signature`
validation, exception normalization, and elapsed-time measurement.

- [ ] **Step 4: Write failing static-tool tests**

In temporary project roots, test:

- `read_file()` reads allowed UTF-8 files and rejects `.env`, traversal, and
  files over the character limit,
- `tree_view()` omits `.git`, virtual environments, and `__pycache__`,
- `code_search()` reports relative path, line, and snippet,
- `find_entrypoints()` finds `main.py` and `train.py`,
- `python_ast_summary()` returns functions, classes, and imports,
- dependency/environment parsers return structured data,
- syntax/compileall checks report success and failure,
- `pytest_collect()` uses `--collect-only` and never runs test bodies.

- [ ] **Step 5: Verify static-tool tests fail**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_static_tools -v
```

Expected: imports fail because static tools do not exist.

- [ ] **Step 6: Implement safe static tools and default registry**

All paths resolve under explicitly supplied roots. Reject secret basenames and
system paths. Use Python APIs where available; subprocess calls use argument
lists, timeout, restricted cwd, and never `shell=True`. Register the tools with
descriptions, schemas, safety levels, and allowed high-level agents.

- [ ] **Step 7: Verify tool tests and existing suite**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_tool_runtime tests.test_static_tools -v
conda run -n paperpilot python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit tool runtime**

```bash
git add schemas runtime tools tests/test_tool_runtime.py tests/test_static_tools.py
git commit -m "feat(tool): add safety-aware tool runtime"
```

## Task 3: Productize LangGraph with Fan-out and Revision

**Files:**
- Create: `graphs/__init__.py`
- Create: `graphs/subgraphs/__init__.py`
- Create: `graphs/subgraphs/product_revision_graph.py`
- Create: `graphs/productize_graph.py`
- Create: `runtime/node_wrappers.py`
- Modify: `pipeline/productize_pipeline.py`
- Create: `tests/test_productize_graph.py`

- [ ] **Step 1: Write failing proposal-graph tests**

Create deterministic fake node dependencies and assert:

- graph compilation succeeds,
- two papers produce two capability-card extraction calls,
- one failing paper appends an error while the other card survives,
- the proposal graph returns `ProductProposal` JSON compatible with current
  proposal construction,
- graph trace records normalize, extraction, synthesis, planning, and proposal
  nodes.

- [ ] **Step 2: Verify proposal tests fail**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_productize_graph.ProductizeProposalGraphTests -v
```

Expected: import failure because `graphs.productize_graph` does not exist.

- [ ] **Step 3: Implement Productize proposal graph**

Use `StateGraph(ProductizeState)` and `Send` for per-paper extraction. Runtime
context supplies agent callables so tests do not require network calls. Merge
capability cards through reducer channels, perform one cross-paper synthesis,
plan products, and build compatibility proposals.

- [ ] **Step 4: Write failing execution/revision tests**

Assert:

- score `>=4.0` finishes without revision,
- low adapter/UI score routes to prototype revision,
- low scope/faithfulness score routes to product-plan revision,
- revision count increments and history records the route,
- the loop stops at `max_revisions`,
- scaffold and inspection run once for the final prototype, not before every
  planning revision.

- [ ] **Step 5: Verify execution tests fail**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_productize_graph.ProductizeExecutionGraphTests -v
```

Expected: failures for missing execution graph behavior.

- [ ] **Step 6: Implement execution and revision graph**

Build and compile the selected-proposal graph with conditional edges from
evaluation. Revision nodes consume evaluation suggestions, rebuild the relevant
structured artifact, append revision history, and terminate deterministically.
Filesystem side effects remain terminal deterministic nodes.

- [ ] **Step 7: Switch Productize compatibility wrappers**

Keep signatures and return values. `generate_proposals()` invokes the proposal
graph; `execute_proposal()` invokes the execution graph; the top-level
composition remains unchanged. Preserve HITL callbacks and output-directory
behavior.

- [ ] **Step 8: Verify Productize graph and regressions**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_productize_graph -v
conda run -n paperpilot python -m unittest tests.test_product_pipeline tests.test_productize_ui -v
conda run -n paperpilot python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit Productize graph**

```bash
git add graphs runtime/node_wrappers.py pipeline/productize_pipeline.py tests/test_productize_graph.py
git commit -m "refactor(productize): orchestrate workflow with LangGraph"
```

## Task 4: Reproduce LangGraph and Command Risk Routing

**Files:**
- Create: `graphs/subgraphs/command_review_graph.py`
- Create: `graphs/reproduce_graph.py`
- Modify: `pipeline/reproduce_pipeline.py`
- Modify: `pipeline/__init__.py`
- Create: `tests/test_reproduce_graph.py`

- [ ] **Step 1: Write failing graph-structure and branch tests**

With fake dependencies, assert:

- graph compilation succeeds,
- research and repository preparation are both direct descendants of the
  parsed-paper node,
- repository understanding receives both paper and repository evidence,
- paper-only repository fallback still reaches planning,
- graph trace contains both branch nodes before repository understanding.

- [ ] **Step 2: Verify branch tests fail**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_reproduce_graph.ReproduceBranchTests -v
```

Expected: import failure because `graphs.reproduce_graph` does not exist.

- [ ] **Step 3: Implement Reproduce graph nodes and joins**

Use `StateGraph(ReproduceState)`. Parse PDF once, fan out to research reasoning
and deterministic repository preparation, join at repository understanding,
then run planning. Preserve resource-link merging and paper-only behavior.

- [ ] **Step 4: Write failing risk-routing tests**

Assert:

- all-low commands route `safe`,
- any medium/high command routes `review`,
- any blocked command routes `blocked`,
- pending human review contains command, purpose, risk level, and cwd,
- no command is automatically executed by the graph,
- execution diagnosis receives planned/not-executed summaries.

- [ ] **Step 5: Verify risk tests fail**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_reproduce_graph.ReproduceRiskRoutingTests -v
```

Expected: missing routing behavior.

- [ ] **Step 6: Implement command review subgraph and remaining nodes**

Use existing `plan_command()` for classification. Safe/review/blocked summary
nodes update state only. Continue to implementation generation, diagnosis, and
deterministic output writing without running commands.

- [ ] **Step 7: Switch Reproduce compatibility wrapper**

Keep `run_reproduce_pipeline()` signature and existing result keys. Convert
input arguments to graph state/context, invoke the graph, and return the
compatibility result. Preserve debug-goal handling, HITL behavior, implementation
model fallback, paper-name output directories, and status semantics.

- [ ] **Step 8: Verify Reproduce graph and regressions**

Run:

```bash
conda run -n paperpilot python -m unittest tests.test_reproduce_graph -v
conda run -n paperpilot python -m unittest tests.test_code_agent tests.test_agent_architecture tests.test_productize_ui -v
conda run -n paperpilot python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit Reproduce graph**

```bash
git add graphs pipeline/reproduce_pipeline.py pipeline/__init__.py tests/test_reproduce_graph.py
git commit -m "refactor(reproduce): orchestrate workflow with LangGraph"
```

## Task 5: CI, Documentation, and Final Verification

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `README_ZH.md`
- Modify: `docs/DEVELOPMENT.md`

- [ ] **Step 1: Update CI**

Compile `graphs/*.py`, `graphs/subgraphs/*.py`, `runtime/*.py`, and all new
tool/schema modules. Keep pytest restricted to `tests/`.

- [ ] **Step 2: Update English and Chinese READMEs**

Document:

- LangGraph as the orchestration layer,
- Productize per-paper fan-out,
- evaluator revision loop,
- Reproduce paper/repository graph branches,
- command-risk routing without automatic execution,
- Tool Registry/Executor safety boundaries,
- deferred ReAct and trace UI work.

- [ ] **Step 3: Update development rules**

Add `graph` and `runtime` commit scopes, update architecture and project tree,
and document state serialization, idempotent node requirements, tool
authorization, and compatibility-wrapper rules.

- [ ] **Step 4: Run complete verification**

```bash
conda run -n paperpilot python -m unittest discover -s tests -v
conda run -n paperpilot pytest tests/ -q
conda run -n paperpilot python -m compileall -q agents graphs runtime pipeline productize schemas tools app.py main.py config.py
conda run -n paperpilot python -c "import app; print('app import ok')"
git diff --check
```

Expected: all tests pass, compileall succeeds, app imports, and diff check is
clean.

- [ ] **Step 5: Run workflow smoke tests**

Run one mock Reproduce flow and one multi-paper Productize flow through public
pipeline APIs. Assert compatibility result keys, graph trace, revision fields,
generated artifacts, and no automatic command execution.

- [ ] **Step 6: Run Streamlit smoke**

Use `streamlit.testing.v1.AppTest` to render Reproduce and Productize modes,
then run a 15-second headless server startup with no traceback.

- [ ] **Step 7: Review against approved design**

Compare `master...HEAD` with
`docs/implementation-plan/2026-06-12-langgraph-phase1-4-design.md`. Fix all
critical and important findings with regression tests first.

- [ ] **Step 8: Commit documentation and CI**

```bash
git add .github/workflows/ci.yml README.md README_ZH.md docs/DEVELOPMENT.md
git commit -m "docs(readme): document LangGraph orchestration"
```

- [ ] **Step 9: Push and create a draft PR**

```bash
git push -u origin codex/langgraph-deep-refactor-phase1-4
gh pr create --draft --base master --head codex/langgraph-deep-refactor-phase1-4 --title "[codex] add LangGraph orchestration" --body-file /tmp/paperpilot-langgraph-pr.md
```

The PR body includes architecture, compatibility, safety, deferred scope, and
exact verification evidence.
