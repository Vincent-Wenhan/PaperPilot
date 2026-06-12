# PaperPilot LangGraph 深度改造方案 v2

## 0. 本版修订说明

这版方案基于当前仓库重新核对后修改。相比上一版，主要调整是：

```text
1. 不再把 Runner 三模式当作从零新增，因为当前 command_runner.py 已经有 RUNNER_MODES、风险分级和 run_command_review 的雏形。
2. 不再强调“新增 8 个高层 Agent”，因为当前 README 和 agents/ 已经完成了 8 个高层 Agent 的收敛。
3. 重点改为：
   - 引入 LangGraph 作为 orchestration layer；
   - 新增 graphs/ 和 runtime/；
   - 把现有 pipeline 包装成 graph；
   - 在现有工具基础上继续扩展 Tool Registry / Tool Executor；
   - 给 Repository Understanding、Execution Diagnosis、Prototype Builder 加 ReAct 工具循环；
   - 给 Productize 增加并行 capability extraction 和 evaluator revise loop；
   - 给 Reproduce 增加 paper/repo 并行、command risk routing 和 HITL interrupt。
```

当前仓库已经具备较好的基础，不建议推翻重写。最合理的方案是：

```text
保留现有高层 Agent + schemas + guidelines + productize scaffold
        ↓
新增 LangGraph orchestration 和 runtime tool layer
        ↓
逐步替换 pipeline 内部串行流程
```

---

## 1. 当前仓库状态判断

根据当前 README，PaperPilot 已经具备：

```text
Reproduce Mode:
  - Research Understanding Agent
  - Repository Understanding Agent
  - Reproduction Planner Agent
  - Execution & Diagnosis Agent
  - Deterministic Report Builder

Productize Mode:
  - generate_proposals()
      Research Synthesizer Agent
      Product Planner Agent
      Capability Cards
      Capability Map
      Method Composition Plan
      JTBD
      Value Proposition
      PRD
      MVP
      MoSCoW

  - execute_proposal()
      Prototype Builder Agent
      Template selection
      deterministic scaffold
      Product Evaluator Agent
      static inspection
      rubric evaluation
```

README 也明确说明：

```text
1. 当前 active reasoning agents 只有 8 个。
2. fragmented predecessor agents 已经放在 agents/legacy/。
3. Repository cloning/scanning、command execution、report writing、product scaffolding、static inspection 都是 deterministic tools 或 builders。
4. Productize Mode 已经支持多 PDF、多 repo 形式、PRD/MVP、proposal review 和 generated_product。
```

这说明前一阶段的“Agent 精简”和“产品理论化”已经基本完成。

当前仍然需要改进的是：

```text
1. pipeline 仍然主要是 Python 函数顺序调用。
2. Productize 虽然分成 generate_proposals 和 execute_proposal，但 evaluator 后还没有自动 revise loop。
3. 多论文 capability extraction 仍然主要由 ResearchSynthesizer 一次处理，不是 per-paper 并行。
4. Reproduce 的 paper analysis 和 repo scan 还没有 graph-level 并行。
5. Repository Understanding Agent 还没有主动 ReAct 读文件、搜代码、分析 AST。
6. Execution & Diagnosis Agent 还没有基于真实 command results 做工具增强诊断。
7. command_runner.py 已有 runner mode 雏形，但还没有和 pipeline / graph / UI 形成完整闭环。
8. 当前仓库还没有 graphs/ 和 runtime/ 目录。
9. requirements.txt 还没有 langgraph 依赖。
```

---

## 2. 本次改造目标

本次改造不是继续加 Agent，而是升级运行时能力：

```text
从：
  serial structured pipeline

升级为：
  LangGraph-based tool-augmented collaborative workflow
```

具体目标：

```text
1. Productize Mode 支持并行多论文 capability extraction。
2. Productize Mode 支持 evaluator-driven revision loop。
3. Reproduce Mode 支持 paper branch 和 repo branch 并行。
4. Repository Understanding Agent 支持 ReAct 工具循环。
5. Execution & Diagnosis Agent 支持 ReAct 诊断循环。
6. command_runner 的 RUNNER_MODES 和 risk assessment 接入 graph routing。
7. HITL 从阶段确认升级为 command/proposal/prototype 的 graph-level interrupt。
8. 工具层扩展为 Tool Registry + Tool Executor，支持文件、代码搜索、代码分析、测试、环境解析、代码生成等工具。
```


---

## 3. 依赖更新

当前 requirements.txt 包含：

```text
streamlit
PyMuPDF
openai
pydantic
python-dotenv
```

需要新增：

```text
langgraph>=0.2
pyyaml>=6
pytest>=8
```

建议 requirements.txt 改成：

```text
streamlit>=1.40,<2
PyMuPDF>=1.24,<2
openai>=1.50,<2
pydantic>=2.0,<3
python-dotenv>=1.0,<2
langgraph>=0.2
pyyaml>=6
pytest>=8
```

暂时不强制引入 LangChain Agent。当前 `LLMClient` 和 `StructuredAgent` 可以继续使用，LangGraph 只负责状态图编排。

---

## 4. 新增目录结构

建议新增：

```text
graphs/
  __init__.py
  productize_graph.py
  reproduce_graph.py
  subgraphs/
    __init__.py
    repo_react_graph.py
    execution_diagnosis_graph.py
    product_revision_graph.py
    command_review_graph.py

runtime/
  __init__.py
  graph_state.py
  node_wrappers.py
  routing.py
  tool_registry.py
  tool_executor.py
  react_loop.py
  collaboration.py
  checkpointing.py
```

保留现有：

```text
agents/
guidelines/
schemas/
pipeline/
productize/
tools/
```

迁移策略：

```text
1. pipeline/ 不删除，先作为兼容 wrapper。
2. 新增 graphs/ 后，pipeline 内部逐步调用 graph runner。
3. app.py 和 main.py 外部 API 尽量不变。
4. 先迁移 Productize，再迁移 Reproduce。
```

---

## 5. Graph State 设计

### 5.1 ProductizeState

新增：

```text
runtime/graph_state.py
```

```python
from typing import Annotated, TypedDict
import operator


class ProductizeState(TypedDict, total=False):
    paper_paths: list[str]
    papers: list[dict]
    paper_texts: list[str]

    repo_urls: list[str]
    repo_scans: list[dict]

    target_user: str
    product_goal: str
    preferred_type: str
    user_idea: str

    capability_cards: Annotated[list[dict], operator.add]
    capability_map: dict
    relationships: list[dict]
    composition_plan: dict
    research_synthesis: dict

    proposals: list[dict]
    selected_proposal: dict
    edited_proposal: dict

    product_plan: dict
    prd: dict
    mvp_scope: dict
    prototype_plan: dict
    template_type: str

    scaffold_result: dict
    inspection: dict
    evaluation: dict

    revision_count: int
    max_revisions: int

    issues: Annotated[list[dict], operator.add]
    tool_logs: Annotated[list[dict], operator.add]
    errors: Annotated[list[str], operator.add]
```

说明：

```text
capability_cards / issues / tool_logs / errors 使用 Annotated list merge，
方便后续并行节点合并结果。
```

### 5.2 ReproduceState

```python
from typing import Annotated, TypedDict
import operator


class ReproduceState(TypedDict, total=False):
    pdf_path: str
    paper_text: str
    paper_name: str

    github_url: str
    repo_path: str
    repo_source: str
    repo_scan: dict

    hardware: str
    gpu_info: str
    goal: str
    user_idea: str

    research_understanding: dict
    repository_understanding: dict
    reproduction_plan: dict

    command_plans: list[dict]
    command_review: dict
    command_results: Annotated[list[dict], operator.add]
    execution_diagnosis: dict

    runner_mode: str
    pending_human_review: dict | None

    report_paths: dict

    issues: Annotated[list[dict], operator.add]
    tool_logs: Annotated[list[dict], operator.add]
    errors: Annotated[list[str], operator.add]
```


---

## 6. Productize Graph 设计

当前 `pipeline/productize_pipeline.py` 已经分为：

```text
generate_proposals()
execute_proposal()
run_productize_pipeline()
```

建议不要一次改坏外部 API，而是在内部切换到 graph。

### 6.1 Productize Graph 总流程

```text
START
  ↓
normalize_inputs
  ↓
parse_or_load_papers
  ↓
scan_repos_if_any
  ↓
extract_capability_cards_parallel
  ↓
synthesize_research
  ↓
plan_product
  ↓
proposal_review
  ↓
build_prototype
  ↓
scaffold_product
  ↓
inspect_product
  ↓
evaluate_product
  ↓
route_after_evaluation
      ├── pass → END
      ├── revise_product_plan → plan_product
      ├── revise_prototype → build_prototype
      ├── fallback_to_comparison_product → build_prototype
      └── max_revision_reached → END_WITH_WARNINGS
```

### 6.2 多论文 capability 并行

当前 `ResearchSynthesizerAgent` 一次处理 normalized_papers。  
建议改成两层：

```text
1. per-paper capability extraction
2. cross-paper synthesis / composition
```

第一版可以不新增正式 Agent，而是在 `ResearchSynthesizerAgent` 内部通过输入控制完成。

节点设计：

```text
prepare_capability_jobs
  ↓
extract_capability_card(paper_i)  # parallel / map
  ↓
merge_capability_cards
  ↓
synthesize_research
```

好处：

```text
1. 多论文时更快。
2. 单篇论文失败不会影响全部。
3. 能在 UI 中展示每篇论文 capability card 的状态。
4. Evaluator 可以定位某一篇论文的 capability card 问题。
```

### 6.3 Product Evaluator revision loop

当前 `execute_proposal()` 已经调用 ProductEvaluatorAgent，但 evaluation 只是最终结果。  
建议加入自动修正：

```text
ProductEvaluatorAgent
  ↓
if overall_score >= 4.0:
    END
elif revision_count < max_revisions:
    route to ProductPlanner or PrototypeBuilder
else:
    END_WITH_WARNINGS
```

路由规则：

```python
def route_after_evaluation(state):
    evaluation = state.get("evaluation", {})
    score = evaluation.get("overall_score", 0)
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 1)
    suggestions = " ".join(evaluation.get("revision_suggestions", []))
    warnings = " ".join(evaluation.get("safety_warnings", []))

    if score >= 4.0:
        return "end"

    if revision_count >= max_revisions:
        return "end_with_warnings"

    text = (suggestions + " " + warnings).lower()

    if any(k in text for k in ["prd", "scope", "paper faithfulness", "unsupported", "target user"]):
        return "revise_product_plan"

    if any(k in text for k in ["ui", "adapter", "mock", "syntax", "readme", "prototype"]):
        return "revise_prototype"

    return "revise_product_plan"
```

### 6.4 Productize 中保留现有 HITL

当前有：

```text
capability confirmation
prototype confirmation
proposal select/edit
```

短期继续使用 `PipelineHITL`。  
中期可以迁移为 LangGraph interrupt：

```text
proposal_review_node
prototype_review_node
```


---

## 7. Reproduce Graph 设计

当前 `pipeline/reproduce_pipeline.py` 是四 Agent 串行流程。  
建议迁移为：

```text
START
  ↓
parse_paper ─────────────┐
  ↓                      ↓
research_understanding   prepare_repository
  ↓                      ↓
  └──────────────→ repository_understanding_react
                         ↓
                  reproduction_planner
                         ↓
                  command_risk_router
                    ├── safe → run_safe_commands
                    ├── review → command_review_interrupt
                    └── blocked → skip_execution
                         ↓
                  execution_diagnosis_react
                         ↓
                  need_more_repo_info?
                    ├── yes → repository_understanding_react
                    └── no → build_outputs
                         ↓
                       END
```

### 7.1 Paper 和 Repo 并行

当前流程先 paper understanding，再 repo prepare。  
改成：

```text
parse_pdf + ResearchUnderstanding
prepare_repository
```

两支可以并行。  
如果 repo 为空，则 repo branch 返回 paper-only evidence。

### 7.2 Repository Understanding ReAct

这是 Reproduce Mode 最值得增强的地方。

当前 `RepositoryUnderstandingAgent` 主要基于 repo_scan。  
升级后它可以在有限循环中调用：

```text
read_file
code_search
python_ast_summary
parse_requirements
parse_environment_yml
find_entrypoints
find_dataset_paths
find_checkpoint_keywords
```

ReAct 流程：

```text
Observe:
  research_understanding
  repo_scan

Decide:
  还需要看哪些文件或搜索哪些关键词？

Act:
  调用 read_file / code_search / ast_summary

Reflect:
  是否已经确认 entrypoints、dependency、dataset、checkpoint、risk？

Final:
  输出 RepositoryUnderstanding
```

限制：

```text
max_steps = 5
read-only tools only
no command execution
no repo modification
max_file_chars
```

### 7.3 Execution & Diagnosis ReAct

当前 diagnosis 输入 `command_results: []`。  
在接入 command runner 后，应改成：

```text
CommandResult
  ↓
ExecutionDiagnosisAgent
  ↓
如果失败：
    code_search(error keyword)
    read_file(related file)
    parse_requirements()
    produce fix suggestions
```

限制：

```text
只诊断，不自动修复官方 repo。
需要修复时只生成 patch suggestion 或 workspace/generated_code。
```


---

## 8. 工具层扩展

当前 tools 已有：

```text
command_runner.py
github_tool.py
guideline_loader.py
llm_client.py
markdown_writer.py
pdf_parser.py
repo_scanner.py
```

其中 `command_runner.py` 已经有：

```text
RUNNER_MODES = ("safe", "review", "sandbox")
risk assessment
plan_command
run_command_review
```

所以新方案不是重写 Runner，而是：

```text
1. 把 command_runner 纳入 Tool Registry。
2. 把 run_command_review 接入 graph command_risk_router。
3. 扩展 Safe Mode 允许 py_compile / compileall / pytest --collect-only 等安全检查。
4. Review Mode 接入 HITL / interrupt。
5. Sandbox Mode 暂时保留接口，后续再实现 Docker / conda。
```

### 8.1 Tool Registry

新增：

```text
runtime/tool_registry.py
runtime/tool_executor.py
schemas/tool_schema.py
```

```python
class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    safety_level: str  # safe / review / sandbox / blocked
    allowed_agents: list[str]
    timeout_seconds: int = 30


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict
    reason: str
    requested_by: str


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    output: dict | str
    error: str = ""
    safety_level: str = "safe"
    elapsed_seconds: float = 0
```

### 8.2 File Tools

新增：

```text
tools/file_tools.py
```

工具：

```text
list_dir
tree_view
read_file
read_many_files
safe_write_file
safe_apply_patch
```

限制：

```text
1. 默认只读 workspace/、uploads/、outputs/、generated_product/。
2. 禁止读取 .env、~/.ssh、系统目录。
3. 限制单文件最大字符数。
4. 写入默认只能写 generated_product/、outputs/、workspace/generated_code/。
5. 修改 clone repo 必须走 Review Mode，第一版可以禁止。
```

### 8.3 Code Search Tools

新增：

```text
tools/code_search_tools.py
```

工具：

```text
code_search
search_imports
find_entrypoints
find_argparse_usage
find_hydra_usage
find_click_usage
find_dataset_paths
find_checkpoint_keywords
find_absolute_paths
find_todo_or_missing
```

第一版用 `pathlib + regex` 即可，不强依赖 ripgrep。

### 8.4 Code Analysis Tools

新增：

```text
tools/code_analysis_tools.py
```

工具：

```text
python_ast_summary
extract_functions_classes
extract_cli_args
dependency_parser
config_parser
framework_detector
import_graph_builder
```

### 8.5 Code Edit Tools

新增：

```text
tools/code_edit_tools.py
```

工具：

```text
generate_file
write_adapter_stub
write_minimal_run_script
write_config_template
apply_patch
validate_patch
```

限制：

```text
1. 默认只能写 generated_product/、outputs/、workspace/generated_code/。
2. 不能直接修改 clone 的 repo。
3. 生成 patch 需要先展示 diff。
4. 真正 apply patch 需要 Review Mode。
```

### 8.6 Test / Validation Tools

新增：

```text
tools/test_tools.py
```

工具：

```text
python_syntax_check
compileall_check
pytest_collect
pytest_dry_run
streamlit_app_check
generated_product_inspect
markdown_link_check
```

其中：

```text
python -m py_compile <file>
python -m compileall <dir>
pytest --collect-only
```

可以作为 Safe Mode 工具。

### 8.7 Env Tools

新增：

```text
tools/env_tools.py
```

工具：

```text
parse_requirements
parse_pyproject
parse_environment_yml
detect_cuda_requirement
detect_python_version
dependency_conflict_check
pip_check_plan
```

第一版只做静态分析，不自动安装依赖。


---

## 9. Agent ReAct 设计

不建议所有 Agent 都 ReAct。  
第一版只给这几个加：

```text
Repository Understanding Agent
Execution & Diagnosis Agent
Prototype Builder Agent
Product Evaluator Agent
```

### 9.1 内部 ReAct 第一版

```python
def run_react_agent(agent, state, tool_executor, max_steps=5):
    for step in range(max_steps):
        action = agent.decide_next_action(state)

        if action.type == "tool_call":
            result = tool_executor.run(action.tool_call)
            state["tool_logs"].append(result)
            state = agent.reflect_on_tool_result(state, result)

        elif action.type == "final":
            return action.output

    return agent.finalize(state)
```

### 9.2 显式 ReAct 子图第二版

后续再把 ReAct 展开为：

```text
observe
  ↓
decide_tool
  ↓
execute_tool
  ↓
reflect
  ↓
continue?
  ├── yes → decide_tool
  └── no → final
```

对应：

```text
graphs/subgraphs/repo_react_graph.py
graphs/subgraphs/execution_diagnosis_graph.py
```

---

## 10. Agent 协作模式

### 10.1 Structured Handoff

继续使用 schema artifact：

```text
ResearchUnderstanding
RepositoryUnderstanding
ReproductionPlan
ExecutionDiagnosis
ResearchSynthesis
ProductPlan
PrototypePlan
ProductEvaluation
```

### 10.2 Shared State Collaboration

通过 graph state 共享：

```text
capability cards
repo evidence
command results
inspection reports
evaluation issues
tool logs
revision history
```

### 10.3 Review Issue

新增：

```python
class ReviewIssue(BaseModel):
    source_agent: str
    target_agent: str
    severity: str
    issue_type: str
    message: str
    required_action: str
```

用途：

```text
Product Evaluator → Product Planner / Prototype Builder
Execution Diagnosis → Repository Understanding / Reproduction Planner
```

### 10.4 Revision Loop

Productize：

```text
Product Planner
  ↓
Prototype Builder
  ↓
Product Evaluator
  ↓
if score low:
    revise Product Planner or Prototype Builder
```

Reproduce：

```text
Reproduction Planner
  ↓
Command Runner
  ↓
Execution Diagnosis
  ↓
if missing repo evidence:
    route back to Repository Understanding ReAct
```


---

## 11. Tools 并行设计

### 11.1 Repo Evidence 并行

并行执行：

```text
read README
parse requirements
parse environment.yml
find entrypoints
find config files
find dataset paths
find checkpoint keywords
find CUDA/custom op signals
```

合并为：

```text
RepositoryEvidenceBundle
```

### 11.2 Multi-paper Capability 并行

```text
paper_1 → capability card
paper_2 → capability card
paper_3 → capability card
```

合并为：

```text
CapabilityCardList
```

### 11.3 Product Inspection 并行

```text
file existence check
syntax check
mock mode check
README run command check
adapter boundary check
requirements check
```

合并为：

```text
ProductInspectionReport
```

### 11.4 Command Validation 并行

```text
command_safety_check
entrypoint_exists_check
cwd_check
timeout_estimation
risk_classification
```

合并为：

```text
CommandReviewBundle
```

---

## 12. 与现有代码的迁移关系

### 12.1 直接保留

```text
agents/structured_agent.py
tools/llm_client.py
tools/pdf_parser.py
tools/github_tool.py
tools/guideline_loader.py
tools/markdown_writer.py
tools/command_runner.py
productize/product_scaffold.py
productize/product_templates.py
productize/product_tester.py
schemas/reproduction_schema.py
schemas/product_schema.py
schemas/composition_schema.py
schemas/evaluation_schema.py
schemas/runner_schema.py
```

### 12.2 包装成 Graph Node

```text
ResearchUnderstandingAgent.run_structured
RepositoryUnderstandingAgent.run_structured
ReproductionPlannerAgent.run_structured
ExecutionDiagnosisAgent.run_structured
ResearchSynthesizerAgent.run_structured
ProductPlannerAgent.run_structured
PrototypeBuilderAgent.run_structured
ProductEvaluatorAgent.run_structured
```

### 12.3 pipeline 作为兼容层

短期：

```python
def run_reproduce_pipeline(...):
    return run_reproduce_graph(...)

def generate_proposals(...):
    return run_productize_proposal_graph(...)

def execute_proposal(...):
    return run_productize_execution_graph(...)
```

这样不需要马上重写 `app.py`。


---

## 13. Streamlit UI 改动建议

### 13.1 Graph Trace 面板

展示：

```text
current node
completed nodes
tool calls
issues
revision count
evaluation score
pending human review
```

### 13.2 Productize 中间结果展示

展示：

```text
Capability Cards
Capability Map
Method Composition
Product Opportunities
Selected Proposal
PRD
MVP / MoSCoW
Prototype Plan
Inspection Report
Evaluation
Revision History
```

### 13.3 Runner Review UI

展示：

```text
Command
Purpose
Risk level
Working directory
Expected output
Blocked reason
Confirm / Reject / Edit
```

---

## 14. 分阶段实施路线

### Phase 1：补依赖和 runtime skeleton

```text
1. requirements.txt 加 langgraph / pyyaml / pytest
2. 新增 graphs/
3. 新增 runtime/
4. 新增 ProductizeState / ReproduceState
5. 新增 node_wrappers.py
```

### Phase 2：工具层升级

```text
1. ToolSpec / ToolCall / ToolResult
2. ToolRegistry
3. ToolExecutor
4. file_tools
5. code_search_tools
6. code_analysis_tools
7. test_tools
8. env_tools
```

### Phase 3：Productize Graph

```text
1. parse/load papers
2. capability extraction parallel
3. synthesize research
4. plan product
5. build prototype
6. scaffold
7. inspect
8. evaluate
9. route/revise loop
```

### Phase 4：Productize revise loop

```text
1. Product Evaluator score threshold
2. revision_count
3. route to Product Planner / Prototype Builder
4. max_revisions
5. revision history
```

### Phase 5：Repository Understanding ReAct

```text
1. read-only tools
2. max_steps = 5
3. read_file / code_search / ast_summary
4. reflect and finalize
```

### Phase 6：Execution Diagnosis ReAct

```text
1. consume real CommandResult
2. search error keyword
3. parse dependency files
4. suggest fix / route back if missing evidence
```

### Phase 7：Reproduce Graph

```text
1. paper/repo branch parallel
2. repo react
3. reproduction planner
4. command risk router
5. HITL command review
6. execution diagnosis loop
7. report builder
```

### Phase 8：CI 和测试更新

新增测试：

```text
tests/test_tool_registry.py
tests/test_file_tools.py
tests/test_code_search_tools.py
tests/test_productize_graph.py
tests/test_reproduce_graph.py
tests/test_command_review.py
```

CI 增加：

```text
python -m py_compile graphs/*.py
python -m py_compile runtime/*.py
python -m py_compile tools/*.py
pytest -q
```

---

## 15. 最小可行改造版本

如果不想一次改太多，最小可行版本是：

```text
1. requirements 加 langgraph。
2. 新增 graphs/productize_graph.py。
3. 新增 runtime/graph_state.py。
4. Productize Graph 支持:
   - generate_proposals graph
   - execute_proposal graph
   - evaluation revise loop
5. 新增 ToolExecutor，但第一版只包装已有 product_tester / command_runner。
6. Repository Understanding ReAct 暂时只做 read_file + code_search 两个工具。
```

这个版本就已经能体现：

```text
LangGraph orchestration
Evaluator revision loop
tool-augmented agent
multi-paper graph flow
```

---

## 16. 本版方案相对上一版的关键变化

```text
上一版：
  更强调从零新增 Runner mode、8 agents、Productize concepts。

本版：
  承认当前仓库已经完成这些基础：
    - 8 high-level agents
    - multi-paper Productize
    - PRD / MVP / MoSCoW
    - mock-first
    - RUNNER_MODES / risk assessment
    - CI / examples / guidelines / schemas

  因此重点改为：
    - LangGraph orchestration
    - runtime/tool layer
    - ReAct loops
    - parallel branches
    - evaluator revision loop
    - graph-level HITL
```

---

## 17. 最终效果

改完后，PaperPilot 会从：

```text
高层 Agent 的串行 pipeline
```

升级为：

```text
LangGraph 状态图驱动的协作式 Agent 系统
```

也就是：

```text
1. 多论文 capability 可以并行生成。
2. Product Evaluator 可以触发 revision。
3. Repository Agent 可以循环读文件、搜代码、分析 AST。
4. Execution Diagnosis Agent 可以根据真实命令结果循环诊断。
5. Command Runner 的 risk assessment 可以决定 safe / review / blocked 路由。
6. HITL 不只是阶段确认，而可以成为 graph 中断点。
7. 工具调用有 Tool Registry、Tool Executor 和 tool logs。
8. 所有中间结果都在 graph state 中可追踪。
```
