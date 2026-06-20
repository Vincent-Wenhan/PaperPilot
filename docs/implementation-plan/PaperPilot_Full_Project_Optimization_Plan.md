# PaperPilot 全项目优化方案：Frontend Workbench + Agent 协作 + 代码能力

## 0. 方案定位

本方案基于当前 PaperPilot 仓库的实际状态编写。当前项目已经不是早期 Streamlit demo，而是已经形成了：

```text
frontend/       Next.js Agent Workbench Preview
backend/        FastAPI facade
graphs/         Reproduce / Productize LangGraph workflows
runtime/        Graph state, routing, tool executor, checkpoints
agents/         高层 Agent
tools/          文件、代码搜索、代码分析、测试、命令执行等工具
schemas/        结构化输出模型
ui/             legacy Streamlit UI
```

因此，本方案不再建议“从 Streamlit 迁移到 Next.js”，而是建议：

```text
在现有 frontend/ + backend/ + graphs/ + runtime/ 基础上，
把 PaperPilot 从 Agent Workbench Preview 打磨成真正的 Research Agent IDE。
```

当前核心问题可以概括为：

```text
1. 后端 Agent 能力已经比较丰富，但前端还没有充分表达这些能力。
2. frontend/ 有 workbench 雏形，但视觉、信息架构、组件拆分还不够成熟。
3. graph / event / tool call / artifact / action approval 没有形成统一体验。
4. Code 能力后端已有基础，但前端还没有真正的 Code Workbench。
5. Productize / Reproduce 有 evaluator、review、diagnosis，但缺少可操作的 revision / patch / approval 闭环。
6. README、requirements、backend、frontend、CI 之间还有一些工程一致性问题。
```

最终目标：

```text
PaperPilot Research Agent IDE

用户不是“上传论文后等报告”，而是在一个工作台里和 Agent 一起完成：
理解论文 → 分析仓库 → 生成计划 → 执行工具 → 检查代码 → 审批修改 → 评估产物 → 修正结果。
```

---

## 1. 当前项目关键观察

### 1.1 当前已经具备的优势

当前 README 已经说明 PaperPilot 支持：

```text
Reproduce Mode:
  - 论文 PDF 解析
  - GitHub repo 浅克隆和扫描
  - 方法和实验拆解
  - Implementation Blueprint
  - bounded reproduction implementation
  - code quality / blueprint coverage
  - command risk routing
  - runner / diagnosis
  - report builder

Productize Mode:
  - 多论文输入
  - Paper Capability Cards
  - Capability Map
  - Method Composition Plan
  - JTBD / Value Proposition
  - PRD / MVP / MoSCoW
  - Product Evaluator
  - bounded revision routing
  - UI spec builder
  - generated_product scaffold
```

当前仓库结构也已经包含：

```text
frontend/
backend/
graphs/
runtime/
tools/
tests/
examples/
```

这说明项目已经具备比较完整的 Agent 系统骨架，下一步不应该继续堆更多 Agent 名字，而应该提高：

```text
1. UI 产品感
2. Agent 可观察性
3. 代码工作区能力
4. 人机协作闭环
5. 工程一致性
```

---

### 1.2 当前最需要修的问题

#### 问题 1：requirements 与 README / backend / graphs 不一致

README 中的启动方式已经包含：

```text
uvicorn backend.main:app --reload --port 8000
```

并且依赖验证命令里包含：

```text
import fitz, langgraph, openai, streamlit, yaml
```

但当前 `requirements.txt` 中仍主要是：

```text
streamlit
PyMuPDF
openai
pydantic
python-dotenv
```

建议优先修正：

```text
fastapi
uvicorn
langgraph
pyyaml
pytest
```

这是最高优先级的工程一致性问题，否则别人按 README 安装后会发现 Workbench / Graph 无法正常启动。

---

#### 问题 2：frontend/ 已经有 Workbench 壳，但产品感不足

当前 frontend 已经有：

```text
三栏 layout
workflow graph
co-planning
event stream
action approval
inspector tabs
artifacts/code/diff/runner/tool/logs/preview panels
```

但问题是：

```text
1. 组件过大，workspace-shell 和 inspector-panel 过于臃肿。
2. 视觉系统不统一，还不像成熟产品。
3. WorkflowGraph 更像静态示意图，不是真实 graph trace。
4. Inspector 还不是真正 Code Workbench。
5. Action Approval 还没有统一抽象为所有高风险动作的机制。
```

---

#### 问题 3：Graph 能力和前端状态没有完全打通

当前 `graphs/reproduce_graph.py` 和 `graphs/productize_graph.py` 已经有比较完整的流程：

```text
Reproduce:
  parse → research/repo evidence → planning → command routing → implementation → review → diagnosis → outputs

Productize:
  paper fan-out → research synthesis → product planning → prototype → evaluation → revision routing → scaffold
```

但前端用户看到的还不完全是这个真实 graph 的状态。需要把：

```text
node_started
node_finished
tool_call
tool_result
human_review_required
revision_started
artifact_created
```

统一成 event stream，并让 WorkflowGraph / Timeline / Inspector 都从同一份事件状态读取。

---

#### 问题 4：代码能力后端有了，前端没有体现出来

`tools/` 中已经有不少代码能力：

```text
file_tools.py
code_search_tools.py
code_analysis_tools.py
code_writer.py
env_tools.py
test_tools.py
command_runner.py
```

但 frontend 还缺少真正的：

```text
File tree
Monaco Editor
Diff Viewer
Patch-first workflow
Syntax check panel
Runner result panel
Tool call trace
```

所以用户感觉“代码能力一般”，并不是后端完全没有能力，而是前端没有把能力组织成 Coding Agent Workbench。

---

#### 问题 5：Evaluator / Diagnosis 的建议没有变成可操作动作

Productize 已经有 Product Evaluator 和 revision routing。  
Reproduce 已经有 code review / sandbox verify / diagnosis。  
但前端还缺少：

```text
1. Evaluation issue cards
2. Revise PRD / Reduce MVP / Revise Prototype / Accept with Warning 按钮
3. Code review issue → generate patch → diff → approve → syntax check 流程
4. Diagnosis issue → route back to repo evidence / planner / patch generator
```

这会让“Agent 配合”和“输出质量提升”看起来不明显。

---

## 2. 参考项目与可借鉴点

下面这些项目可以作为 PaperPilot 后续优化参考。文档中直接放 GitHub 链接，方便后续查看。

---

### 2.1 Vercel AI Chatbot

GitHub:

```text
https://github.com/vercel/ai-chatbot
```

可借鉴点：

```text
1. Next.js App Router 项目结构
2. shadcn/ui + Tailwind 设计系统
3. 现代 AI Chat UI
4. Tool call / structured output 展示方式
5. 多模型 provider UI
6. Chat + artifact 的组织方式
```

PaperPilot 不应该变成普通聊天机器人，但可以借鉴它的前端工程结构和 AI 交互设计。

---

### 2.2 Dify

GitHub:

```text
https://github.com/langgenius/dify
```

可借鉴点：

```text
1. Workflow canvas
2. Node status / workflow run log
3. Tool / model provider abstraction
4. AI app builder 思路
5. Observability / debug panel
```

PaperPilot 可以做一个 Dify-lite 的只读/半可编辑 graph trace：

```text
点击 LangGraph 节点 → 看 input / output / tool calls / issues / revision reason。
```

---

### 2.3 OpenHands

GitHub:

```text
https://github.com/OpenHands/openhands
```

官网：

```text
https://openhands.dev/
```

可借鉴点：

```text
1. Coding Agent Workspace
2. File explorer + code editor + runner/terminal + agent actions
3. 多 backend / sandbox execution
4. Agent action trace
5. 真实工程任务的执行闭环
```

PaperPilot 不需要做到 OpenHands 那么完整，但应该把右侧 Inspector 做成轻量版 Code Workbench。

---

### 2.4 Magentic-UI / MagenticLite

GitHub:

```text
https://github.com/microsoft/magentic-ui
```

Microsoft Research blog:

```text
https://www.microsoft.com/en-us/research/blog/magentic-ui-an-experimental-human-centered-web-agent/
```

可借鉴点：

```text
1. Human-in-the-loop
2. Co-planning
3. Action approval
4. User takeover
5. Safe sandbox
6. Agent 行动透明化
```

PaperPilot 最适合借鉴：

```text
Agent 先生成 plan → 用户确认 → Agent 执行 → 高风险动作进入 approval → 用户 approve/edit/reject。
```

---

### 2.5 LangGraph

GitHub:

```text
https://github.com/langchain-ai/langgraph
```

Docs:

```text
https://docs.langchain.com/oss/python/langgraph/overview
```

可借鉴点：

```text
1. Stateful agent orchestration
2. Durable execution
3. Streaming
4. Human-in-the-loop
5. Routing
6. Parallelization
7. Evaluator-optimizer pattern
8. Agent/tool loop
```

PaperPilot 已经有 LangGraph，因此 UI 和 backend event schema 应该围绕 LangGraph 的运行状态来设计。

---

### 2.6 RepoMaster

GitHub:

```text
https://github.com/wanghuacan/RepoMaster
```

Paper:

```text
https://arxiv.org/abs/2505.21577
```

可借鉴点：

```text
1. GitHub repo 自主探索
2. Function-call graph
3. Module dependency graph
4. Hierarchical code tree
5. 按需检索核心代码，而不是把整个 repo 塞给 LLM
```

PaperPilot 的 Repository Understanding Agent 可以借鉴：

```text
repo evidence bundle
function/class summary
entrypoint graph
dependency summary
dataset/checkpoint path evidence
```

---

## 3. 总体优化目标

### 3.1 产品体验目标

从：

```text
Preview shell
```

升级为：

```text
Product-quality Research Agent IDE
```

具体目标：

```text
1. 页面视觉统一，像一个真正产品。
2. 用户一眼知道当前 run 状态。
3. 用户能看到 Agent 如何协作。
4. 用户能查看、检查、修改生成代码。
5. 用户能审批风险动作。
6. 用户能根据 evaluator issue 主动修改产物。
7. 用户能复盘每次 run 的 trace、artifacts、actions、patches。
```

---

### 3.2 Agent 交互目标

从：

```text
Run Agents → 等待结果
```

升级为：

```text
Plan → Run → Observe → Approve → Revise → Verify
```

交互流程：

```text
用户输入任务
  ↓
Agent 生成计划
  ↓
用户确认 / 修改计划
  ↓
Graph 执行
  ↓
前端展示 node status + tool calls
  ↓
遇到风险动作进入 Action Approval
  ↓
生成 artifacts / code
  ↓
Evaluator / Diagnosis 给出 issues
  ↓
用户选择 revise / patch / accept / downgrade
```

---

## 4. 最高优先级工程修复

### 4.1 修 requirements

建议改成：

```text
streamlit>=1.40,<2
PyMuPDF>=1.24,<2
openai>=1.50,<2
pydantic>=2.0,<3
python-dotenv>=1.0,<2
fastapi>=0.115,<1
uvicorn[standard]>=0.30,<1
langgraph>=0.2
pyyaml>=6
```

新增：

```text
requirements-dev.txt
```

内容：

```text
pytest>=8
```

---

### 4.2 修 CI

CI 中加入：

```text
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
pytest -q
```

前端加入：

```text
cd frontend
npm ci
npm run build
```

---

### 4.3 README 同步

README 中明确：

```text
1. Legacy Streamlit startup
2. Workbench backend startup
3. Workbench frontend startup
4. Required Python deps
5. Required Node deps
6. Mock mode / real mode
```

避免用户按 README 启动失败。

---

## 5. Frontend 优化方案

### 5.1 引入设计系统

当前 `frontend/package.json` 比较轻量，建议加：

```bash
npm install @tanstack/react-query
npm install @monaco-editor/react
npm install react-diff-viewer-continued
npm install tailwindcss postcss autoprefixer
npm install clsx tailwind-merge class-variance-authority
npm install @radix-ui/react-tabs @radix-ui/react-dialog @radix-ui/react-dropdown-menu
```

第二阶段再考虑：

```bash
npm install xterm xterm-addon-fit
```

---

### 5.2 拆分大组件

当前 `workspace-shell.tsx` 和 `inspector-panel.tsx` 过大。建议拆成：

```text
frontend/components/layout/
  app-shell.tsx
  top-bar.tsx
  project-sidebar.tsx
  center-workspace.tsx
  right-inspector.tsx

frontend/components/run/
  run-intake-form.tsx
  run-summary-card.tsx
  run-status-bar.tsx
  run-mode-switcher.tsx

frontend/components/chat/
  agent-chat.tsx
  artifact-mention-input.tsx

frontend/components/workflow/
  workflow-graph.tsx
  workflow-node-card.tsx
  workflow-timeline.tsx
  node-detail-panel.tsx

frontend/components/approval/
  action-approval-drawer.tsx
  approval-card.tsx

frontend/components/inspector/
  inspector-shell.tsx
  artifacts-panel.tsx
  code-panel.tsx
  diff-panel.tsx
  runner-panel.tsx
  tool-call-panel.tsx
  logs-panel.tsx
  preview-panel.tsx

frontend/components/code/
  file-tree.tsx
  code-editor.tsx
  diff-viewer.tsx
  patch-actions.tsx
  syntax-check-card.tsx
```

拆分的目的不是形式主义，而是让 UI 可以继续打磨。

---

### 5.3 新页面结构

最终 UI 推荐：

```text
Left Sidebar:
  Project / Papers / Repos / Runs / Settings

Center Workspace:
  Agent Chat
  Editable Plan
  Workflow Graph
  PRD / MVP / Product Design

Right Inspector:
  Artifacts
  Code Workbench
  Diff Viewer
  Runner Review
  Tool Calls
  Logs
  Preview
```

---

## 6. Runtime Event / Graph Trace 优化方案

### 6.1 统一 AgentEvent

新增统一事件结构：

```ts
type AgentEvent = {
  id: string;
  runId: string;
  node: string;
  agent?: string;
  type:
    | "node_started"
    | "node_finished"
    | "node_failed"
    | "tool_call"
    | "tool_result"
    | "human_review_required"
    | "action_approved"
    | "action_rejected"
    | "revision_started"
    | "artifact_created"
    | "patch_proposed"
    | "patch_applied";
  status: "pending" | "running" | "success" | "waiting_review" | "failed" | "revised";
  message: string;
  payload?: Record<string, unknown>;
  timestamp: string;
};
```

---

### 6.2 EventBus

后端新增：

```text
backend/services/event_service.py
```

负责：

```text
emit event
list events
subscribe events
persist events
```

短期可以用 JSONL：

```text
backend/storage/events.jsonl
```

---

### 6.3 WorkflowGraph 真实联动

新增 API：

```text
GET /api/runs/{run_id}/graph
GET /api/runs/{run_id}/events
GET /api/runs/{run_id}/events?after=<event_id>
```

前端从 events 计算 node status：

```ts
type GraphNodeState = {
  id: string;
  label: string;
  agent?: string;
  status: "pending" | "running" | "success" | "failed" | "waiting_review" | "revised";
  startedAt?: string;
  finishedAt?: string;
  inputArtifacts?: string[];
  outputArtifacts?: string[];
  toolCalls?: AgentEvent[];
  issues?: ReviewIssue[];
};
```

点击节点显示：

```text
Node Detail
  - Node name
  - Agent
  - Status
  - Input artifacts
  - Output artifacts
  - Tool calls
  - Errors
  - Revision reason
  - Related files
```

---

## 7. Code Workbench 优化方案

### 7.1 Code Panel

功能：

```text
1. File tree
2. Monaco Editor
3. Language detection
4. Read-only / editable mode
5. Explain this file
6. Ask Agent to patch
7. Run syntax check
8. Download file / folder
```

API：

```text
GET  /api/runs/{run_id}/files
GET  /api/runs/{run_id}/files/content?path=
POST /api/runs/{run_id}/files/explain
POST /api/runs/{run_id}/checks/syntax
```

第一版建议只做 read-only Monaco Editor，先把观感和文件浏览打通。

---

### 7.2 Diff / Patch-first

所有代码修改走 patch-first：

```text
Agent proposes patch
  ↓
Diff Panel 展示 old/new
  ↓
Action Approval
  ↓
Apply patch
  ↓
Run py_compile / compileall
  ↓
Execution Diagnosis 总结
```

API：

```text
POST /api/runs/{run_id}/patches/propose
POST /api/runs/{run_id}/patches/apply
GET  /api/runs/{run_id}/patches
```

安全策略：

```text
generated_product/          可以 apply patch
workspace/generated_code/   可以 apply patch
cloned repo                 只生成 patch 文件，不直接 apply
```

---

### 7.3 Runner Panel

Runner Panel 不开放任意 shell，只展示受控执行：

```text
Command
Purpose
Risk
Working directory
Expected output
stdout
stderr
Exit code
Diagnosis
```

命令类型：

```text
safe:
  python --version
  pip --version
  python -m py_compile
  python -m compileall
  pytest --collect-only

review:
  python demo.py --help
  python eval.py --dry-run

blocked:
  rm -rf
  curl | bash
  shell pipes
  destructive commands
```

---

## 8. Action Approval 统一化

### 8.1 PendingAction

```ts
type PendingAction = {
  id: string;
  runId: string;
  agent: string;
  type:
    | "run_command"
    | "apply_patch"
    | "write_file"
    | "download_resource"
    | "install_dependency"
    | "open_external_url";
  risk: "safe" | "review" | "sandbox" | "blocked";
  reason: string;
  payload: Record<string, unknown>;
  status: "pending" | "approved" | "rejected" | "edited";
};
```

---

### 8.2 Action Approval Drawer

UI：

```text
Action Request

Agent: Reproduction Planner
Action: apply_patch
Risk: review
Reason: generated_product/app.py has syntax issue

Buttons:
  Approve
  Edit
  Reject
```

API：

```text
GET  /api/runs/{run_id}/actions
POST /api/actions/{action_id}/approve
POST /api/actions/{action_id}/reject
POST /api/actions/{action_id}/edit
```

---

## 9. Productize 质量闭环

### 9.1 Productize 页面重构

拆成四个视图：

```text
Research
  Paper Capability Cards
  Capability Map
  Method Composition

Product
  JTBD
  Value Proposition
  PRD
  MVP / MoSCoW

Prototype
  UI Spec
  Generated App Structure
  Adapter Boundary
  Preview

Evaluation
  Scores
  Issues
  Revision Actions
  Revision History
```

---

### 9.2 Evaluation Issue Cards

每条 issue 变成可操作卡片：

```text
Issue: MVP scope is too broad
Severity: medium
Target: Product Planner
Suggestion: Reduce features to upload → mock output → explanation → download report

Actions:
  [Reduce MVP Scope]
  [Revise PRD]
  [Revise Prototype]
  [Accept with Warning]
```

这些按钮触发 graph route：

```text
Product Evaluator → Product Planner
Product Evaluator → Prototype Builder
Product Evaluator → Finish with warning
```

---

## 10. Reproduce 质量闭环

### 10.1 Code Quality Panel

Reproduce 结果页新增：

```text
Implementation Blueprint
Generated files
Blueprint coverage score
Syntax status
Smoke test status
Sandbox verify
Code review verdict
Revision suggestions
Second review result
Final diagnosis
```

### 10.2 Repository Evidence Trace

展示 Repository Understanding 的证据链：

```text
✓ Found train.py
✓ Found eval.py
✓ Parsed requirements.txt
✓ Found argparse arguments
⚠ Checkpoint path unclear
⚠ Dataset preprocessing missing
```

对应 tool calls：

```text
code_search("argparse")
read_file("README.md")
python_ast_summary("train.py")
parse_requirements("requirements.txt")
find_dataset_paths()
```

---

## 11. Backend 持久化方案

### 11.1 RunStore

当前可先用 JSONL，不必直接上数据库：

```text
backend/storage/
  runs.jsonl
  events.jsonl
  actions.jsonl
  artifacts.jsonl
  patches.jsonl
```

后续再换 SQLite：

```text
runs
events
actions
artifacts
patches
files
```

---

### 11.2 新增服务

```text
backend/services/event_service.py
backend/services/action_service.py
backend/services/patch_service.py
backend/services/graph_service.py
```

已有服务可以保留，但统一 `run_id / event_id / action_id / artifact_id`。

---

## 12. 测试和 CI 方案

新增测试：

```text
tests/test_workbench_event_stream.py
tests/test_workbench_graph_api.py
tests/test_workbench_actions_api.py
tests/test_workbench_patch_api.py
tests/test_frontend_contracts.py
```

CI：

```yaml
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
pytest -q

cd frontend
npm ci
npm run build
```

---

## 13. 分阶段实施计划

### Phase 0：先修能跑的问题

```text
1. 修 requirements.txt：fastapi / uvicorn / langgraph / pyyaml。
2. 增加 requirements-dev.txt：pytest。
3. CI 加 backend import check。
4. CI 加 frontend npm build。
5. README 同步说明 runtime/dev deps。
```

这是最高优先级。

---

### Phase 1：Frontend 设计系统 + 组件拆分

```text
1. 引入 Tailwind / shadcn 或至少统一 CSS tokens。
2. 拆分 workspace-shell.tsx。
3. 拆分 inspector-panel.tsx。
4. 增加 RunSummaryCard。
5. 增加 RunStatusBar。
6. 增加更清晰的 ProjectSidebar。
```

目标：UI 观感明显提升。

---

### Phase 2：事件流 + 真实 WorkflowGraph

```text
1. 定义统一 AgentEvent。
2. 后端所有 node/tool/action/artifact emit event。
3. 前端 graph 从 events 更新 node status。
4. 点击 node 显示 node detail。
5. Timeline 和 Graph 使用同一份 event source。
```

目标：Agent 协作看得见。

---

### Phase 3：Code Workbench v1

```text
1. Code panel 加 file tree。
2. 引入 Monaco Editor。
3. 展示 generated_product / generated_code。
4. 加 syntax check button。
5. 展示 check result。
6. 支持 download file/folder。
```

目标：代码能力可见。

---

### Phase 4：Patch-first + Action Approval

```text
1. 定义 PendingAction。
2. runner / patch / write file 统一进入 approval。
3. 增加 diff viewer。
4. apply patch 后自动 py_compile。
5. patch history 进入 artifacts。
```

目标：代码修改可控。

---

### Phase 5：Productize Quality Workbench

```text
1. Productize 结果拆成 Research / Product / Prototype / Evaluation。
2. Evaluation issue 做成 cards。
3. 每条 issue 提供 revision buttons。
4. revision 触发 graph route。
5. 展示 revision history。
```

目标：Productize 输出质量可被用户主动改善。

---

### Phase 6：Reproduce Quality Workbench

```text
1. 展示 Implementation Blueprint。
2. 展示 generated files。
3. 展示 sandbox verify。
4. 展示 code review verdict。
5. 展示 revision suggestions。
6. 展示 second review。
```

目标：Reproduce 的代码能力更可信。

---

### Phase 7：Demo 和文档

```text
1. examples/screenshots 加真实截图。
2. README 顶部加入 Workbench GIF。
3. examples/sample_run 加真实 JSON。
4. docs/ 添加 Workbench user flow。
5. docs/ 添加 architecture diagram。
```

目标：GitHub 展示效果明显提升。

---

## 14. 最小可执行版本 v1.1

建议先做：

```text
1. 修 requirements / CI。
2. 拆 frontend 大组件。
3. WorkflowGraph 绑定真实 events。
4. Code tab 换 Monaco read-only。
5. Productize Evaluation issue cards。
6. ActionApproval 抽象成 PendingAction。
7. README 加真实截图。
```

这 7 个点做完，PaperPilot 的观感、可信度和 Agent 协作体验会明显提升。

---

## 15. 最终定位

PaperPilot 最终应该定位为：

```text
PaperPilot Research Agent IDE

A research-to-reproduction and research-to-product agent workspace
with paper understanding, repository analysis, PRD-driven productization,
coding-agent-style code workbench, workflow visualization,
and human-in-the-loop action approval.
```

核心体验：

```text
用户不是“上传论文，等待报告”，
而是和 Agent 一起完成：
理解论文 → 分析仓库 → 生成计划 → 执行工具 → 检查代码 → 审批修改 → 评估产物 → 修正结果。
```
