# PaperPilot 当前代码可用性审查与 UI/Agent Workbench 修改方案

## 0. 审查目标

本次审查不是泛泛地评价“架构好不好”，而是围绕三个具体问题：

```text
1. 当前代码和文档描述是否一致？
2. 每个关键模块是否真的能 work？
3. 如果要做成我期待的 Research Agent IDE，现在代码应该怎么改？
```

本报告基于当前 GitHub 仓库的代码和文档进行静态审查。  
注意：我没有在本地完整执行 `pip install`、`npm build`、`pytest`，所以关于“能不能 work”的判断是基于代码路径、依赖、API 绑定、组件数据来源和工程一致性的审查结论，而不是实际运行日志。

---

## 1. 总体结论

当前 PaperPilot 已经不是早期 Streamlit demo，而是已经形成了一个较完整的 Agent Workbench 结构：

```text
frontend/       Next.js Workbench
backend/        FastAPI facade
graphs/         Reproduce / Productize LangGraph workflows
runtime/        graph state, routing, tool executor
tools/          file / code / env / test / runner tools
agents/         high-level reasoning agents
schemas/        structured schemas
ui/             legacy Streamlit UI
```

但是从“是否真正能用、效果是否足够好”的角度看，当前项目仍处于：

```text
Workbench Prototype / Preview
```

还不是完整的：

```text
Production-quality Research Agent IDE
```

核心判断：

| 维度 | 当前状态 | 评价 |
|---|---|---|
| 功能完整性 | 70% | 主流程、graph、tools、frontend/backend 都有雏形 |
| 工程可运行性 | 60% | 依赖、run state、API 绑定仍有风险 |
| UI/UX 完成度 | 55% | 页面结构已搭好，但产品感和真实交互不足 |
| Agent 协作可见性 | 55% | graph 有了，但 node/tool/action 没完全打通 |
| 代码能力 | 60% | tools 有基础，但 Code Workbench 没完全可用 |
| 输出质量闭环 | 50% | evaluator/review 有了，但用户可操作 revision 不完整 |
| 生产成熟度 | 45% | 仍偏 demo/prototype，需要 run-scoped storage 和更强 CI |

一句话总结：

```text
当前项目已经“有 Workbench 的样子”，
但还没有形成“真实可用的 Workbench 闭环”。
```

---

## 2. 我期待的 UI 目标图

我期待 PaperPilot 最终变成一个三栏式 Research Agent IDE：

```text
左侧：Project / Papers / Repos / Runs / Settings
中间：Workflow Graph / Agent Chat / Editable Plan / PRD-MVP / Product Design
右侧：Artifacts / Code Workbench / Diff Viewer / Runner / Tool Calls / Logs / Preview
```

UI 目标图如下：

![PaperPilot Expected UI Mockup](./paperpilot_expected_ui_mockup.png)

如果在 ChatGPT 沙盒中查看，图片文件为：

```text
paperpilot_expected_ui_mockup.png
```

---

## 3. 当前代码是否真的能 work？

### 3.1 安装和依赖：存在高风险问题

当前 `requirements.txt` 在 GitHub Raw 中显示为单行。  
如果真实文件确实是一整行，例如：

```text
streamlit>=1.40,<2 fastapi>=0.115,<1 uvicorn[standard]>=0.30,<1 ...
```

那么 `pip install -r requirements.txt` 很可能解析失败。  
Python requirements 文件应该一行一个依赖。

建议改成：

```txt
streamlit>=1.40,<2
fastapi>=0.115,<1
uvicorn[standard]>=0.30,<1
PyMuPDF>=1.24,<2
openai>=1.50,<2
socksio>=1.0,<2
pydantic>=2.0,<3
python-dotenv>=1.0,<2
langgraph>=0.2,<2
pyyaml>=6,<7
pytesseract>=0.3,<1
```

并新增：

```txt
# requirements-dev.txt
pytest>=8,<9
```

结论：

```text
当前安装链路可能不稳定。
这是最高优先级修复项。
```

---

### 3.2 CI：已经覆盖更多模块，但仍需要实际验证

当前 CI 已经比早期完整，包含：

```text
backend job:
  pip install -r requirements.txt
  pip install -r requirements-dev.txt
  py_compile app/main/config
  py_compile agents/tools/pipeline/productize/schemas/runtime/graphs/backend
  pytest tests/

frontend job:
  cd frontend
  npm ci
  npm run build
```

这是好的方向。

但是如果 `requirements.txt` 真的是单行，CI 的 Python install 阶段会直接失败。  
所以先修 requirements，再看 CI 是否能绿。

建议补充：

```yaml
- name: Smoke import
  run: |
    python - <<'PY'
    import fastapi, uvicorn, langgraph, yaml, fitz, openai, streamlit
    print("imports ok")
    PY
```

结论：

```text
CI 方向对，但必须先确保依赖文件格式正确。
```

---

### 3.3 Backend：API facade 有了，但仍是半真实 Workbench

当前 `backend/main.py` 已经有：

```text
FastAPI app
CORS
runs/actions/artifacts/checks/commands/files/llm/patches/uploads routers
WebSocket /ws/runs/{run_id}
```

这说明 backend 主体是存在的。

但问题在于：

```text
1. run_service 仍然是 InMemoryRunService。
2. run/action/result 主要存在内存中。
3. 后端重启后 run 状态丢失。
4. WebSocket 还不像完整实时流。
5. event_service 有 JSONL，但 run/actions/patches/files 没有完全统一到 durable store。
```

当前 `event_service.py` 已经有 JSONL event persistence，这是很好的进展：

```text
events_{run_id}.jsonl
emit
list_events
subscribe
```

但 `run_service.py` 仍然保留：

```text
_runs: dict
_events: dict
_actions: dict
_results: dict
```

结论：

```text
Backend 可以跑 demo，但还不是稳定 workspace。
需要把 run/action/patch/artifact 全部 run-scoped persistence。
```

---

### 3.4 WebSocket / Event Stream：存在，但实时性不足

当前前端 `WorkspaceShell` 主要使用：

```text
setInterval(..., 1800)
fetchRun()
fetchRunEvents()
fetchRunGraph()
```

WebSocket 存在，但更像“已有 events 发送 + idle”，不是 graph 执行时的真正实时事件流。

当前体验会是：

```text
用户看到状态刷新，
但不是流式 agent trace。
```

建议：

```text
1. 保留 polling 作为 fallback。
2. WebSocket 改成真正 subscribe event_service。
3. 每个 graph node/tool/action 都 emit structured event。
4. 前端通过 event_id 做增量更新，而不是每次全量 fetch。
```

结论：

```text
事件流现在能支撑 preview，但还不够支撑真实 Agent IDE。
```

---

### 3.5 WorkflowGraph：有图，但仍不够真实

当前 `graph_service.py` 已经能从 events 推导 graph node 状态，这是一个进步。

但核心问题是：  
graph node 目前部分依赖自然语言 message 匹配，例如：

```text
message contains "capability card" → capability_cards
message contains "prd" → prd
message contains "sandbox" → command_routing
message contains "code review" → review
```

这种方式可用，但不够可靠。  
如果 Agent 文案变了，graph 映射就可能错。

应改成所有事件直接带结构化 node id：

```json
{
  "event_type": "node_started",
  "node": "repository_understanding",
  "graph": "reproduce",
  "agent": "Repository Understanding Agent",
  "status": "running",
  "message": "Reading repository evidence"
}
```

结论：

```text
WorkflowGraph 当前能看，但还不是真正严格的 LangGraph trace。
需要结构化 node events。
```

---

### 3.6 Frontend：组件已经开始优化，但还有 mock 和半真实交互

当前 `frontend/components/` 已经有：

```text
layout/
inspector/
code/
approval/
productize/
reproduce/
```

这是好的。

但 `workspace-shell.tsx` 仍然很重，仍承担：

```text
run form
upload
llm config
polling
timeline events
graph enrichment
chat messages
approval status
local UI actions
```

这会导致后续扩展困难。

另外，`inspector-panel.tsx` 仍然大量使用 mock 数据：

```text
artifacts
codeFiles
patchPreview
runnerReview
toolCalls
```

这意味着：

```text
Artifacts 有部分 API-backed。
Code 有部分 API-backed。
Diff 仍主要是 mock patchPreview。
Runner 仍主要是 preview 状态。
Tool Calls 仍主要来自 mock toolCalls。
```

结论：

```text
Frontend 已经有形，但还没有完全从 mock preview 切到真实 backend-driven workspace。
```

---

### 3.7 Action Approval：组件有了，但真实绑定不完整

当前 `ActionApprovalDrawer` 和 `ApprovalCard` 已经存在。

但是 `workspace-shell.tsx` 中仍有硬编码 action：

```text
approveAction("act_smoke_test")
editAction("act_smoke_test", ...)
rejectAction("act_smoke_test")
```

这会导致真实 run 中 action id 不匹配。  
如果后端实际 action id 是 `act_{run_id}_...`，前端就无法真正控制。

更严重的是 catch 后忽略错误，前端仍然显示本地成功：

```text
// Keep local preview responsive even when the API server is offline.
```

这对 preview 友好，但对真实产品不可信。

建议：

```text
1. 新增 GET /api/runs/{run_id}/actions。
2. 前端从真实 pending actions 渲染 drawer。
3. 去掉 act_smoke_test 硬编码。
4. approve/edit/reject 后必须以后端结果为准。
5. 失败时显示错误，不要本地假成功。
```

结论：

```text
Action Approval 还没真正 work，只是半真实 preview。
```

---

### 3.8 Patch / Diff：后端有 apply，但缺审批和自动检查

当前 `patch_service.py` 可以：

```text
propose_patch
apply_patch
```

但 `apply_patch()` 会直接写文件：

```text
resolved.write_text(patch.new_content, encoding="utf-8")
```

缺少：

```text
1. Action Approval。
2. 自动 syntax check。
3. patch history 持久化。
4. apply 后事件记录。
5. failed rollback。
```

正确流程应该是：

```text
Agent proposes patch
  ↓
PatchProposal created
  ↓
PendingAction(type="apply_patch") created
  ↓
User approve
  ↓
apply_patch
  ↓
python syntax check / compileall
  ↓
event: patch_applied / check_passed / check_failed
```

结论：

```text
Patch 功能有后端雏形，但还不是安全可靠的 patch-first workflow。
```

---

### 3.9 Files / Artifacts：没有严格 run scoped

`backend/routers/files.py` 中：

```text
def list_files(run_id):
    del run_id
    return file_service.list_files()
```

这说明 file listing 当前没有真正按 run_id 隔离。

问题：

```text
1. 不同 run 的 files 可能混在一起。
2. 用户打开历史 run 时看不到严格对应的文件。
3. 不适合长期 workspace。
```

建议输出统一 run 目录：

```text
workspace/runs/{run_id}/
  inputs/
  outputs/
  generated_code/
  generated_product/
  patches/
  logs/
```

所有 files/artifacts/patches/commands 都基于 `run_id` 查这个目录。

结论：

```text
现在 files 能用作 preview，但不适合真实多 run workspace。
```

---

### 3.10 LLM 配置：API key 落盘有风险

当前 `backend/routers/llm.py` 会把 `api_key` 保存到：

```text
llm_config.json
```

这对本地 demo 方便，但有安全隐患：

```text
1. 容易误提交。
2. 容易被复制到 demo 文件。
3. 不适合多人/课程展示场景。
```

建议：

```text
1. 默认不保存 api_key。
2. 只保存 base_url / model / implementation_model。
3. api_key 只读环境变量或浏览器 session。
4. .gitignore 明确加入 llm_config.json。
5. UI 中提示：API key is session-only.
```

结论：

```text
当前能用，但安全设计不够好。
```

---

### 3.11 Productize Evaluation：组件有了，但仍是 mock issues

当前 `evaluation-issues.tsx` 已经有：

```text
IssueCard
Reduce MVP Scope
Revise PRD
Revise Prototype
Accept with Warning
ProductizeTabs
```

这是很好的方向。

但文件中仍有：

```text
MOCK_ISSUES
getMockIssues()
```

所以当前 issue cards 更像前端 mock，而不是从真实 Product Evaluator 结果生成。

建议：

```text
1. 从 run result / evaluation artifact 读取 evaluator output。
2. detected_problems → issue cards。
3. revision_suggestions → action buttons。
4. safety_warnings → high severity issue。
5. 按钮触发后端 evaluation actions。
```

结论：

```text
Productize Quality Workbench 方向对，但还没真正接上 evaluator。
```

---

## 4. 当前项目“真实可用性”分级

| 模块 | 当前可用性 | 结论 |
|---|---:|---|
| Legacy Streamlit | 较高 | 稳定 demo 可用 |
| FastAPI backend | 中等 | 能跑 preview，但状态持久化不足 |
| Next.js frontend | 中等 | UI 壳子可用，但 mock 残留较多 |
| WorkflowGraph | 中等 | 能显示，但不是严格 graph trace |
| Event stream | 中等偏低 | 有 JSONL 和 polling，实时性不足 |
| Action approval | 偏低 | 组件有，但真实 action 绑定不足 |
| Code Workbench | 中等偏低 | Monaco/Code 组件有，但 workflow 未闭环 |
| Patch workflow | 偏低 | 后端能 apply，但缺审批/检查/rollback |
| Productize evaluation | 偏低 | UI 有 issue cards，但仍是 mock |
| Reproduce quality loop | 中等 | graph 结构有，但前端表达不足 |
| CI/CD | 中等 | 覆盖面提升，但依赖格式需确认 |
| 安全性 | 中等偏低 | API key 保存和 patch apply 需加强 |

---

## 5. 按目标 UI 反推当前代码修改建议

### 5.1 左侧 Project Sidebar

目标图中左侧应包含：

```text
New Project
Projects
Recent Runs
Settings
Profile
```

当前已有 `ProjectSidebar`，但仍偏输入面板和导航混合。

建议：

```text
1. ProjectSidebar 只负责 workspace navigation。
2. Run input form 独立成 RunIntakePanel。
3. Recent Runs 从 backend list runs 获取。
4. 每个 run 显示 mode/status/time。
```

新增 API：

```text
GET /api/runs
```

---

### 5.2 中间 Workflow Area

目标图中中间是主工作区：

```text
Workflow / Chat / Code / Artifacts / Logs / Evaluation tabs
```

当前 `CenterWorkspace` 已存在，但应进一步明确：

```text
Workflow tab:
  React Flow graph + selected node detail

Chat tab:
  artifact-aware chat

Code tab:
  main code workbench shortcut

Evaluation tab:
  product/reproduce quality issues
```

优先做：

```text
Workflow tab 完全绑定真实 graph events。
```

---

### 5.3 右侧 Current Step Drawer

目标图中右侧浮层显示：

```text
Current Step
Agent
Progress
ETA
Recent Events
```

当前可以从 selected graph node + latest events 生成。

新增组件：

```text
components/workflow/current-step-panel.tsx
```

数据来源：

```text
GET /api/runs/{run_id}/graph
GET /api/runs/{run_id}/events?after=
```

---

### 5.4 底部 Code / Terminal 面板

目标图中底部是：

```text
Code Explorer
Code Editor
Terminal / Results
```

当前 Inspector 已经有 Code/Runner tabs，但不如图中直观。

建议：

```text
1. Code Workbench 可以从右侧 Inspector 抽出来，作为 bottom dock。
2. Inspector 负责 node detail/action/evaluation。
3. CodeDock 负责 file tree/editor/runner。
```

如果暂时不重构布局，则先把 Inspector 的 Code tab 做真：

```text
FileTree + Monaco + SyntaxCheck + PatchActions
```

---

### 5.5 移动端适配

目标图中右侧也展示移动端状态。

当前 Next.js UI 应至少支持：

```text
桌面：三栏
平板：左侧折叠 + 中右两栏
手机：tabs 模式
```

建议：

```css
@media (max-width: 900px) {
  layout: single-column;
  sidebar: drawer;
  inspector: bottom sheet;
}
```

---

## 6. 最优先修复清单

### P0：会不会跑

```text
1. 确认并修正 requirements.txt 为一行一个依赖。
2. CI 跑通 pip install + pytest。
3. CI 跑通 frontend npm ci + npm run build。
4. 修 frontend build 报错。
```

---

### P1：真实数据替换 mock

```text
1. Inspector Tool Calls 从真实 events 读取。
2. DiffPanel 从真实 patch API 读取。
3. RunnerPanel 从真实 actions/commands 读取。
4. Productize IssueCard 从真实 evaluation 读取。
5. 删除或隔离 mock-data fallback，不要在正常 run 中出现。
```

---

### P2：Action Approval 闭环

```text
1. 增加 GET /api/runs/{run_id}/actions。
2. 去掉 act_smoke_test 硬编码。
3. PendingAction 统一 run_command/apply_patch/write_file/download_resource。
4. approve/reject/edit 必须以后端返回为准。
5. action 状态写入 event stream。
```

---

### P3：Patch-first 闭环

```text
1. propose_patch 创建 PendingAction。
2. apply_patch 只能由 approved action 触发。
3. apply 后自动 syntax check。
4. 失败时保留错误和 rollback suggestion。
5. patch history 进入 run artifacts。
```

---

### P4：Structured Graph Events

```text
1. 所有 graph nodes emit node_started/node_finished。
2. 所有 tools emit tool_call/tool_result。
3. evaluator emit evaluation_issue。
4. revision router emit revision_started。
5. graph_service 不再依赖 message 关键词。
```

---

### P5：Run-scoped workspace

```text
workspace/runs/{run_id}/
  inputs/
  outputs/
  generated_code/
  generated_product/
  patches/
  logs/
```

改造：

```text
files API
artifacts API
patch API
command output API
```

---

### P6：安全性

```text
1. 不保存 api_key 到 llm_config.json。
2. llm_config.json 加入 .gitignore。
3. apply patch 必须 approval。
4. file API 必须 run scoped。
5. command API 只能走 runner safety。
```

---

## 7. 建议实施顺序

### Week 1：稳定运行链路

```text
1. 修 requirements。
2. 修 CI。
3. 确认 npm build。
4. 确认 backend start。
5. 确认 createRun → events → graph → artifacts 基本链路。
```

### Week 2：真实 Workbench 数据流

```text
1. Tool Calls 接真实 events。
2. Runner 接真实 actions。
3. Diff 接真实 patch API。
4. Productize issues 接真实 evaluation。
5. 去掉主要 mock fallback。
```

### Week 3：Patch / Approval / Check 闭环

```text
1. propose_patch → PendingAction。
2. approve → apply_patch。
3. apply → syntax_check。
4. check result → events/logs。
5. UI 展示 patch history。
```

### Week 4：UI polish

```text
1. 按目标 UI 图调整布局。
2. 左侧 project/run nav。
3. 中间 workflow node detail。
4. 右侧 current step/evaluation/action。
5. 底部 code/terminal dock。
6. mobile responsive。
```

---

## 8. 最小可交付版本 v1.2

建议定义为：

```text
PaperPilot Workbench v1.2
```

必须满足：

```text
1. README 安装命令可跑通。
2. CI backend/frontend 全绿。
3. Create run 后能看到真实 event timeline。
4. WorkflowGraph 节点状态来自真实 events。
5. Tool Calls tab 来自真实 events。
6. Action Approval 使用真实 pending actions。
7. DiffPanel 使用真实 patches。
8. Patch apply 必须 approval。
9. Productize issue cards 来自真实 evaluation。
10. File/Artifact 至少按 run_id 做软隔离。
```

达到这个标准后，才可以说：

```text
PaperPilot Workbench 真的能用。
```

---

## 9. 结论

当前项目不是方向错，而是“实现闭环还没有打通”。

最关键的问题不是再加 Agent，而是：

```text
真实状态流：
  graph node → event → UI graph/timeline

真实动作流：
  proposed action → approval → execution → result

真实代码流：
  file → patch → approval → apply → check

真实质量流：
  evaluation issue → revise action → graph rerun → history
```

只要把这四条流打通，PaperPilot 的 UI、Agent 协作、代码能力和最终输出质量都会明显提高。

