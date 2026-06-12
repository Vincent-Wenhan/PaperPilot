# LangGraph Phase 1-4 Refactor Design

## Status

Approved for implementation on `codex/langgraph-deep-refactor-phase1-4`.

## Goal

Upgrade PaperPilot from function-sequenced structured pipelines to
LangGraph-based orchestration while preserving the existing public APIs,
high-level agents, Pydantic artifacts, deterministic builders, output
persistence, and Streamlit flows.

This delivery covers the agreed Phase 1-4 boundary:

1. runtime and graph skeleton,
2. tool schemas, registry, executor, and safe static tools,
3. Productize graph with per-paper fan-out and evaluator revision,
4. Reproduce graph with parallel paper/repository preparation and command-risk
   routing.

Repository and diagnosis ReAct loops and the Streamlit graph-trace panel are
explicitly deferred.

## Migration Approach

Use a compatibility-wrapper migration.

- Add `graphs/` and `runtime/` as new internal orchestration layers.
- Keep active agents, schemas, guidelines, `productize/`, and deterministic
  tools.
- Keep `pipeline/` as the public compatibility layer.
- Keep the signatures and result keys of `generate_proposals()`,
  `execute_proposal()`, `run_productize_pipeline()`,
  `run_reproduce_pipeline()`, and `run_paperpilot()`.
- Move orchestration into graphs without moving rendering and artifact-writing
  responsibilities into graph state.

The graph nodes call existing domain functions or focused node helpers. They do
not duplicate agent prompts, schemas, renderers, scaffold logic, or output
builders.

## Dependencies

Add:

```text
langgraph>=0.2,<2
pyyaml>=6,<7
pytest>=8,<9
```

The implementation uses the current official Graph API:

- `StateGraph`, `START`, and `END`,
- TypedDict state with `Annotated` reducers,
- conditional edges,
- `Send` for map-reduce fan-out,
- optional `InMemorySaver` checkpointer.

Graph nodes must be idempotent because checkpoint resume can re-run a node from
its beginning. Filesystem side effects remain in terminal deterministic nodes
and use existing backup/write behavior.

## Directory Structure

```text
graphs/
├── __init__.py
├── productize_graph.py
├── reproduce_graph.py
└── subgraphs/
    ├── __init__.py
    ├── command_review_graph.py
    └── product_revision_graph.py

runtime/
├── __init__.py
├── graph_state.py
├── node_wrappers.py
├── routing.py
├── tool_registry.py
├── tool_executor.py
├── collaboration.py
└── checkpointing.py

schemas/
└── tool_schema.py

tools/
├── file_tools.py
├── code_search_tools.py
├── code_analysis_tools.py
├── test_tools.py
└── env_tools.py
```

The two subgraphs are bounded routing components, not full ReAct loops.

## Graph State

### Shared Reducers

Use `Annotated[list[T], operator.add]` for append-only channels:

- errors,
- issues,
- tool logs,
- capability cards,
- command results,
- revision history.

Nodes return partial updates, never whole copied states.

### ProductizeState

The state stores normalized papers, capability jobs/cards, synthesis,
proposals, selected proposal, product/prototype plans, scaffold and inspection
results, evaluation, revision counters, issues, logs, errors, and compatibility
result data.

Runtime-only objects such as `LLMClient`, callbacks, and `PipelineHITL` do not
enter serializable state. They are provided through an immutable graph runtime
context.

### ReproduceState

The state stores PDF/repository inputs, independently produced paper and
repository evidence, structured planning artifacts, command plans and risk
routes, implementation bundle, output paths, issues, logs, errors, and the
compatibility result.

## Runtime Context

Define dataclass contexts for each graph containing:

- `LLMClient`,
- progress callback,
- optional `PipelineHITL`,
- output path,
- implementation options,
- optional tool executor.

This keeps state checkpoint-friendly and avoids serializing clients or
callbacks.

## Node Wrappers

`runtime/node_wrappers.py` provides:

- stage progress reporting,
- structured-agent fallback behavior,
- LLM attempt/failure accounting,
- stage-qualified error updates,
- Pydantic-to-JSON conversion,
- compatibility result merging.

It preserves the existing `LLMClientError` behavior, including endpoint/model
short-circuiting after a blocking failure.

## Tool Runtime

### Schemas

Add Pydantic models:

- `ToolSpec`,
- `ToolCall`,
- `ToolResult`,
- `ReviewIssue`.

Safety levels are `safe`, `review`, `sandbox`, and `blocked`.

### Registry

`ToolRegistry` supports explicit registration, duplicate rejection, lookup,
agent authorization, and listing. The default registry exposes only the tools
implemented in this delivery.

### Executor

`ToolExecutor`:

1. resolves the tool,
2. verifies the requesting agent,
3. enforces the declared safety level,
4. validates keyword arguments against the tool signature,
5. records elapsed time,
6. normalizes success/error output to `ToolResult`.

Review and sandbox tools are not executed unless the caller explicitly opts
into that safety level. Blocked tools never execute.

### Tools in This Delivery

File tools:

- `list_dir`,
- `tree_view`,
- `read_file`,
- `read_many_files`.

Code search tools:

- `code_search`,
- `find_entrypoints`,
- `find_dataset_paths`,
- `find_checkpoint_keywords`,
- `find_todo_or_missing`.

Code analysis tools:

- `python_ast_summary`,
- `extract_functions_classes`,
- `extract_cli_args`,
- `parse_dependency_file`.

Validation tools:

- `python_syntax_check`,
- `compileall_check`,
- `pytest_collect`,
- `generated_product_inspect`.

Environment tools:

- `parse_requirements`,
- `parse_pyproject`,
- `parse_environment_yml`,
- `detect_cuda_requirement`,
- `detect_python_version`.

All tools are deterministic. File reads are restricted to project-controlled
roots and reject secrets and traversal. No clone repository is modified.

## Productize Graph

### Proposal Graph

```text
START
  -> normalize_inputs
  -> prepare_capability_jobs
  -> Send(extract_capability_card per paper)
  -> synthesize_research
  -> plan_product
  -> build_proposals
  -> END
```

Each paper capability job invokes `ResearchSynthesizerAgent` with one paper.
The merged capability cards and normalized papers then feed one cross-paper
synthesis node. A failed paper produces an error and fallback card without
discarding successful papers.

`generate_proposals()` invokes this graph and returns the existing
`list[ProductProposal]`.

### Execution Graph

```text
START
  -> prepare_selected_proposal
  -> select_template
  -> build_prototype
  -> scaffold_product
  -> inspect_product
  -> evaluate_product
  -> route_after_evaluation
       -> finish
       -> revise_product_plan
       -> revise_prototype
       -> finish_with_warnings
```

The default threshold is `overall_score >= 4.0`; default `max_revisions` is 1.
Revision suggestions route scope, target-user, or faithfulness issues to the
product-plan revision node. UI, adapter, mock, syntax, README, or prototype
issues route to prototype revision.

Every revision appends a structured history entry. Scaffold side effects occur
only after the revised plan/prototype is ready. Evaluation after revision
reuses the new inspection output.

`execute_proposal()` invokes this graph and returns the existing result
dictionary.

`run_productize_pipeline()` remains the compatibility composition of proposal
generation and execution.

## Reproduce Graph

```text
START
  -> parse_paper
  -> [research_understanding, prepare_repository] in parallel
  -> repository_understanding
  -> reproduction_planner
  -> command_risk_router
       -> safe_summary
       -> review_summary
       -> blocked_summary
  -> reproduction_implementation
  -> execution_diagnosis
  -> build_outputs
  -> END
```

The repository branch may start after PDF parsing and runs independently of
research reasoning. Repository understanding joins both branches because it
uses repository evidence plus paper understanding when available.

Command risk routing classifies planned commands with the existing
`plan_command()` logic. This delivery records safe/review/blocked routes and
pending review metadata but does not automatically broaden execution. Existing
Runner UI remains the place where commands are confirmed and run.

Existing stage-level `PipelineHITL` confirmations remain supported inside
nodes. Optional graph interruption is exposed only by explicit graph-runner
configuration with a checkpointer and thread ID; default pipeline calls never
pause unexpectedly.

The implementation-generation stage remains deterministic in where it writes
and never runs generated code.

## Checkpointing

`runtime/checkpointing.py` exposes:

- `build_checkpointer(enabled: bool)`,
- `build_graph_config(thread_id: str | None)`.

Default compatibility calls compile without persistence. Tests and future UI
flows may enable `InMemorySaver`. Durable database checkpointing is deferred.

## Error Handling

- Every agent node produces a schema-valid fallback.
- Tool failures return `ToolResult(success=False)` and append a tool log.
- Parallel paper failures do not cancel successful capability cards.
- Graph routing has deterministic defaults for missing scores or suggestions.
- Revision loops always terminate at `max_revisions`.
- Terminal artifact nodes report write failures without erasing prior state.
- Pipeline wrappers preserve existing `pipeline_status` semantics.

## Compatibility

The following remain stable:

- public function signatures unless new optional keyword-only arguments are
  added,
- existing result keys used by `app.py`,
- output directory conventions,
- proposal selection/edit UI,
- Productize backup behavior,
- Reproduce paper-only behavior,
- deterministic mock outputs,
- eight active high-level reasoning agents.

Graph-specific keys such as `graph_trace`, `tool_logs`, `issues`, and
`revision_history` may be added to results without removing old keys.

## Testing

Test-first coverage includes:

- graph-state reducers,
- tool schema validation,
- registry authorization and duplicate handling,
- executor safety enforcement and normalized errors,
- file root/secret/path restrictions,
- code-search and AST extraction,
- validation and environment tools,
- Productize `Send` fan-out and partial failure,
- evaluator routing and max-revision termination,
- Reproduce branch order/parallel readiness,
- command risk routing,
- compatibility wrappers and result keys,
- full existing test suite,
- compileall and Streamlit import/startup smoke.

CI compiles `graphs/`, `runtime/`, new tools, and schemas, then runs all tests.

## Documentation

Update:

- `README.md`,
- `README_ZH.md`,
- `docs/DEVELOPMENT.md`,
- `.github/workflows/ci.yml`.

The README will describe LangGraph as orchestration only, not as a replacement
for PaperPilot's agents or deterministic safety layer.

## Deferred Work

Not included in this delivery:

- open-ended ReAct loops,
- repository-editing tools,
- automatic patch application,
- automatic command execution from the Reproduce graph,
- Docker/Conda sandbox implementation,
- durable database checkpointers,
- Streamlit graph-trace visualization,
- graph-level proposal/prototype interrupt migration.

These require separate specs after the graph foundation is stable.
