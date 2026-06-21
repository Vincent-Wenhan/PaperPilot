# PaperPilot 当前真实问题与改进建议文档

## 0. 文档目的

本文件整理的是当前 PaperPilot 仓库中**经过重新核对后仍然成立的真实问题**，以及对应的修改建议。

这版文档刻意不再重复已经修好的问题。  
例如：Sidebar 已经基本导航化、Action Approval 已经开始接真实 actions、LLM API key 已经不再落盘、Files API 已经开始使用 run_id、Productize issues 已经可以从 run result 生成，这些不再作为主要问题提出。

当前判断：

```text
PaperPilot 目前已经达到 Workbench Preview 水平，
但还没有完全达到稳定、漂亮、闭环完整的 Research Agent IDE 水平。
```

当前完成度大致：

```text
整体完成度：约 75%
核心架构：基本正确
前端 Workbench：已成型，但仍需 polish 和去 mock
后端 API：有基础，但部分闭环未封口
Event / Graph：有雏形，但实时性和结构化还需加强
Code / Patch：组件和服务都有，但审批与验证闭环仍需加强
```

---

## 1. 已经基本符合要求的部分

### 1.1 Sidebar 已经基本改对

当前 `frontend/components/layout/project-sidebar.tsx` 已经主要是导航：

```text
Projects
Papers
Repos
Runs
Agents
Settings
```

Run 表单已经不再主要塞在 Sidebar 中，而是拆到了 `RunIntakeDrawer`。  
所以“Sidebar 仍然混合大量输入表单”这个问题已经基本不成立。

后续建议只是 polish：

```text
1. Projects / Runs 使用真实 run 列表。
2. 当前 active run 高亮。
3. 增加最近 run 状态和 mode 标识。
4. 底部 session 区域可以更像产品级账户区。
```

---

### 1.2 TopBar 已经接近目标 UI

当前 `frontend/components/layout/top-bar.tsx` 已经包含：

```text
breadcrumb
mode selector
run id
elapsed time
New Run button
avatar
```

这已经接近目标 UI。

后续优化：

```text
1. Run status pill 可以更醒目。
2. Timer 可以实时刷新。
3. 可以显示 current model / backend connected 状态。
4. New Run 按钮可以有 dropdown：Reproduce / Productize / Debug。
```

---

### 1.3 Action Approval 已经开始接真实 actions

当前 `workspace-shell.tsx` 已经使用：

```ts
fetchRunActions(runId)
```

并且把真实 `ApiAction` 映射为 `PendingAction`，传给 `ActionApprovalDrawer`。  
这说明 Action Approval 已经不是单纯前端 mock。

后续问题不是“没有接真实 actions”，而是：

```text
Patch direct apply endpoint 仍然可以绕过 approval。
```

这个会在后面列为真实问题。

---

### 1.4 LLM API key 已经不再落盘

当前 `backend/routers/llm.py` 中：

```text
get_llm_config 返回 api_key=""
save_llm_config 只保存 base_url / model / implementation_model
```

也就是说 API key 不再写入 `llm_config.json`。  
这已经符合安全要求。

---

### 1.5 Files API 已经开始使用 run_id

当前 `backend/routers/files.py` 已经把 `run_id` 传给：

```text
file_service.list_files(run_id=run_id)
file_service.read_content(..., run_id=run_id)
```

并不是完全忽略 run_id。

后续建议不是“完全没 run_id”，而是：

```text
当前仍然是通过 result/action/workspace roots 推导文件范围，
如果要做更稳定的项目空间，后续可以统一到 workspace/runs/{run_id}/。
```

---

### 1.6 Productize issues 已经能从真实 run result 生成

当前 `frontend/components/productize/evaluation-issues.tsx` 已经提供：

```ts
issuesFromRunResult(result)
```

它会读取：

```text
detected_problems
revision_suggestions
safety_warnings
```

并转成 `EvaluationIssue[]`。

所以“Productize issues 完全是 mock”这个判断已经不成立。  
真实问题是：

```text
Issue buttons 是否能真正触发后端 revision / graph rerun，目前仍不完整。
```

---

### 1.7 Run state 已经有一定持久化

虽然 `run_service.py` 类名还是 `InMemoryRunService`，但当前代码里已经有：

```text
RUN_STATE_PATH = STORAGE_DIR / "run_state.json"
```

也就是说当前并不是完全内存态。  
后续如果只做本地 workbench demo，这种 JSON state 已经够用。  
如果要做更稳定的多项目 workspace，再考虑 SQLite。

---

## 2. 确认仍然存在的真实问题

---

## P0-1. requirements.txt 格式仍然可能导致安装失败

### 问题

当前 GitHub raw 中 `requirements.txt` 显示为单行：

```text
streamlit>=1.40,<2 fastapi>=0.115,<1 uvicorn[standard]>=0.30,<1 ...
```

这不是标准 requirements 格式。  
`pip install -r requirements.txt` 需要一行一个依赖。

### 影响

```text
1. 用户按 README 安装可能失败。
2. CI 的 pip install 可能失败。
3. 项目第一步就不可复现。
```

### 建议修改

改成：

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

`pytest` 建议放到 `requirements-dev.txt`：

```txt
pytest>=8,<9
```

### 优先级

```text
P0，必须马上修。
```

---

## P0-2. ci.yml 格式仍然可能不是合法 GitHub Actions YAML

### 问题

当前 GitHub raw 中 `.github/workflows/ci.yml` 也显示为单行：

```yaml
name: CI on: push: pull_request: jobs: backend: ...
```

正常 GitHub Actions YAML 必须是多行结构。

### 影响

```text
1. GitHub Actions 可能无法正确解析。
2. backend/frontend build 不能作为质量保障。
3. 无法证明项目真的能 work。
```

### 建议修改

改成：

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Check Python syntax
        run: |
          python -m compileall app.py main.py config.py
          python -m compileall agents tools pipeline productize schemas runtime graphs backend ui

      - name: Run tests
        run: pytest tests/ -v --tb=long

  frontend:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install and build frontend
        run: |
          cd frontend
          npm ci
          npm run build
```

### 优先级

```text
P0，必须马上修。
```

---

## P1-1. WebSocket 仍然不是持续实时 event stream

### 当前情况

当前 `backend/main.py` 的 `/ws/runs/{run_id}` 逻辑是：

```python
for event in run_service.list_events(run_id):
    await websocket.send_json(event.model_dump(mode="json"))

await asyncio.sleep(0.15)
await websocket.send_json({
    "run_id": run_id,
    "event_type": "stream_idle",
    ...
})
```

也就是说：

```text
WebSocket 只发送已有 events，然后发送 stream_idle。
它没有持续订阅 event_service 的新事件。
```

### 影响

目标 Workbench 需要：

```text
graph node 执行
  → event emitted
  → websocket immediately pushes
  → WorkflowGraph / Activity 更新
```

当前更像：

```text
前端 polling + WebSocket replay
```

这对 preview 可用，但还不是实时 Agent Workbench。

### 建议修改

`event_service.py` 已经有 `subscribe / unsubscribe`，可以直接用：

```python
@app.websocket("/ws/runs/{run_id}")
async def run_event_stream(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[WorkbenchEvent] = asyncio.Queue()

    def on_event(event: WorkbenchEvent) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    event_service.subscribe(run_id, on_event)
    try:
        for event in event_service.list_events(run_id):
            await websocket.send_json(event.model_dump(mode="json"))

        while True:
            event = await queue.get()
            await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        return
    finally:
        event_service.unsubscribe(run_id, on_event)
```

### 优先级

```text
P1，高优先级。
```

---

## P1-2. Patch direct apply endpoint 仍然可以绕过 Action Approval

### 当前情况

当前后端已经有安全轨：

```text
PendingAction(type="apply_patch")
  → approve
  → run_service.execute_action
  → patch_service.apply_patch
```

这很好。

但同时 `backend/routers/patches.py` 仍然暴露：

```text
POST /api/patches/{run_id}/apply/{patch_id}
```

它会直接调用：

```python
patch_service.apply_patch(patch_id)
```

并且当前 router 中 `run_id` 被 `del run_id`，没有真正用来校验 patch 是否属于当前 run。

### 影响

这导致 patch 有两条路径：

```text
安全路径：
  propose → PendingAction → approve → apply

绕过路径：
  POST /api/patches/{run_id}/apply/{patch_id} → 直接 apply
```

目标 Workbench 要求所有写文件动作都走 Action Approval，所以 direct apply endpoint 不符合要求。

### 建议修改

三种可选方案：

#### 方案 A：删除 direct apply endpoint

只允许通过 action approval 执行 patch。

```python
# 删除:
# POST /api/patches/{run_id}/apply/{patch_id}
```

#### 方案 B：direct apply 只创建 PendingAction

```python
@router.post("/{run_id}/apply/{patch_id}")
def request_apply_patch(run_id: str, patch_id: str):
    patch = patch_service.get_patch(patch_id)
    if patch is None or patch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Patch not found")

    action = run_service.create_patch_action(run_id, patch_id)
    return action
```

#### 方案 C：要求 approved action_id

```python
POST /api/patches/{run_id}/apply/{patch_id}?action_id=...
```

然后校验：

```text
action exists
action.run_id == run_id
action.patch_id == patch_id
action.status == approved
```

推荐方案：

```text
方案 B 或 A。
```

### 优先级

```text
P1，高优先级。
```

---

## P1-3. PatchApplyResult 结构不够支撑 UI

### 当前情况

`patch_service.apply_patch()` 已经做了 Python syntax check，并把结果拼进 `message`：

```text
Patch applied to generated workspace file. Syntax check passed.
```

但 `PatchApplyResult` 主要字段还是：

```text
patch_id
path
applied
message
```

### 影响

UI 想展示：

```text
Syntax passed
Syntax failed
失败文件
失败原因
检查日志
```

但当前只能从 `message` 里解析，不够结构化。

### 建议修改

扩展 schema：

```python
class PatchApplyResult(BaseModel):
    patch_id: str
    path: str
    applied: bool
    message: str
    syntax_ok: bool = True
    syntax_failures: list[dict[str, str]] = Field(default_factory=list)
```

`patch_service.apply_patch()` 返回：

```python
return PatchApplyResult(
    patch_id=patch_id,
    path=patch.path,
    applied=True,
    message=message,
    syntax_ok=check_ok,
    syntax_failures=[] if check_ok else [{"path": patch.path, "error": check_msg}],
)
```

同时 emit event：

```text
patch_applied
syntax_check_passed / syntax_check_failed
```

### 优先级

```text
P1，高优先级。
```

---

## P2-1. Inspector / Runner / ToolCall 仍依赖 mock-data 类型和 fallback

### 当前情况

虽然现在很多 panel 已经接 API，但部分组件仍然 import mock-era 类型：

```text
RunnerPanel:
  ApprovalRequest
  RunnerReview
  WorkflowStatus from "@/lib/mock-data"

ToolCallPanel:
  ToolCall from "@/lib/mock-data"

InspectorPanel:
  approvalRequest
  mockArtifacts
  codeFiles
  patchPreview
  runnerReview
  mockToolCalls
```

### 影响

这不是致命 bug，但会让真实 run 和 preview fallback 边界不清楚。  
用户可能看不出自己看到的是后端真实数据还是 mock 数据。

### 建议修改

新增真实 UI 类型：

```ts
export type WorkbenchToolCallEvent = {
  id: string;
  runId: string;
  node: string;
  agent: string;
  tool: string;
  input: Record<string, unknown>;
  output?: Record<string, unknown>;
  status: "running" | "success" | "failed";
  timestamp: string;
};

export type RunnerActionView = {
  id: string;
  runId: string;
  agent: string;
  type: "run_command" | "apply_patch";
  command?: string;
  patchId?: string;
  path?: string;
  risk: "safe" | "review" | "sandbox" | "blocked";
  status: string;
  executionStatus: string;
  reason: string;
};
```

改造：

```text
RunnerPanel 不再依赖 mock-data。
ToolCallPanel 不再依赖 mock-data。
InspectorPanel 真实 run 下不 fallback 到 mock。
mock 只用于 no-run preview 或 dedicated mock route。
```

### 优先级

```text
P2，中高优先级。
```

---

## P2-2. Productize revision buttons 还没有形成完整后端闭环

### 当前情况

Productize issues 已经可以从真实 run result 生成。  
但是 issue card 上的：

```text
Revise PRD
Reduce MVP Scope
Revise Prototype
Accept with Warning
```

是否能真正触发后端 graph rerun / revision route，目前还没有完整闭环。

### 影响

用户可以看到 evaluator feedback，但不能真正通过按钮驱动：

```text
Evaluator issue
  → revise PRD / prototype
  → graph rerun
  → new evaluation
  → revision history
```

这会导致 Productize 输出质量改善不明显。

### 建议新增后端 API

```text
POST /api/runs/{run_id}/revision
```

请求体：

```ts
type RevisionRequest = {
  issue_id: string;
  action:
    | "revise_prd"
    | "reduce_mvp_scope"
    | "revise_prototype"
    | "accept_with_warning";
  instruction?: string;
};
```

后端逻辑：

```text
revise_prd:
  route to Product Planner

reduce_mvp_scope:
  route to Product Planner with scope reduction instruction

revise_prototype:
  route to Prototype Builder

accept_with_warning:
  finish and record accepted warning
```

前端：

```ts
async function requestRevision(runId: string, request: RevisionRequest) {
  const response = await fetch(`/api/runs/${runId}/revision`, {
    method: "POST",
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error("Revision request failed");
  return response.json();
}
```

### 优先级

```text
P2，中高优先级。
```

---

## P2-3. Graph events 仍有 legacy fallback，需要进一步结构化

### 当前情况

`graph_service.py` 已经支持 structured node id，这是好的。  
但仍保留 message keyword fallback，用于兼容 `agent_progress` human-readable events。

### 影响

Fallback 本身不是错，但如果 pipeline 主要还是发：

```text
agent_progress
message: "Generating PRD..."
```

那么 graph state 仍可能受文案影响。

### 建议

逐步让每个 graph node 显式 emit：

```json
{
  "event_type": "node_started",
  "graph": "productize",
  "node": "product_planner",
  "agent": "Product Planner Agent",
  "status": "running",
  "message": "Generating PRD and MVP scope",
  "payload": {
    "input_artifacts": ["research_synthesis"],
    "expected_outputs": ["prd", "mvp_scope"]
  }
}
```

保留 fallback 作为 legacy compatibility，但不要依赖它。

### 优先级

```text
P2，中优先级。
```

---

## P3-1. Files API 虽然使用 run_id，但还不是严格统一 run workspace

### 当前情况

Files API 已经使用 run_id，`file_service` 也会基于 run result、actions、workspace/runs 等推导 roots。

这已经可用于本地 Workbench。

但如果目标是更稳定的项目空间，建议统一文件结构：

```text
workspace/runs/{run_id}/
  inputs/
  outputs/
  generated_code/
  generated_product/
  patches/
  logs/
```

### 影响

当前推导式 roots 可能导致：

```text
1. 不同 run 的 artifacts 边界不够清晰。
2. 历史 run 文件恢复不够稳定。
3. 前端 file tree 不容易表达 workspace 层级。
```

### 建议

短期：

```text
保留当前推导式 roots。
```

中期：

```text
所有新 run 输出都写入 workspace/runs/{run_id}/。
```

### 优先级

```text
P3，中等优先级。
```

---

## 3. 最小修复清单

下一步建议只做这些真实问题：

```text
P0:
  1. 修 requirements.txt 为多行。
  2. 修 ci.yml 为合法多行 YAML。
  3. 确认 pip install / pytest / npm build 全通过。

P1:
  4. WebSocket 改为 event_service.subscribe 持续推送。
  5. 禁止 patch direct apply 绕过 approval。
  6. PatchApplyResult 增加 syntax_ok / syntax_failures。
  7. patch applied / syntax check result 写入 events。

P2:
  8. RunnerPanel / ToolCallPanel 去 mock-data 类型。
  9. 真实 run 下 Inspector 不静默 fallback 到 mock。
  10. Productize revision buttons 接后端 revision endpoint。
  11. graph nodes 逐步 emit structured node_started/node_finished。

P3:
  12. 新 run 输出逐步统一到 workspace/runs/{run_id}/。
```

---

## 4. 不建议再纠结的问题

以下问题当前不是主要矛盾：

```text
1. Sidebar 是否已经导航化：已经基本可以。
2. TopBar 是否接近目标 UI：已经接近。
3. Monaco / DiffViewer 是否已经引入：已经引入。
4. ActionApproval 是否完全 mock：已经接真实 actions。
5. LLM API key 是否保存到文件：已经不保存 key。
6. Productize issue 是否完全 mock：已经能从 run result 生成。
7. run state 是否完全内存：已经有 run_state.json。
```

不要再把精力浪费在这些已经修过的点上。

---

## 5. 验收标准

修完上述真实问题后，可以用下面标准验收。

### 安装与 CI

```text
pip install -r requirements.txt 成功
pip install -r requirements-dev.txt 成功
pytest tests/ 成功
cd frontend && npm ci && npm run build 成功
GitHub Actions 正常运行
```

### Workbench 实时性

```text
后端运行中产生 event
WebSocket 立即推送
WorkflowGraph / ActivityPanel 自动更新
不依赖纯 polling
```

### Patch-first

```text
propose patch 后产生 PendingAction
不 approve 不能 apply
approve 后 apply
apply 后自动 syntax check
UI 展示 syntax result
events 中出现 patch_applied / syntax_check_passed
```

### Productize Revision

```text
Productize evaluator 产生 issues
IssueCard 显示真实 issues
点击 Revise PRD / Revise Prototype 后后端生成 revision event
UI 显示 revision history
```

### Mock 边界

```text
无 active run 时可以 mock preview
有真实 run 时不静默 fallback 到 mock
UI 明确显示 Preview / Real Run 状态
```

---

## 6. 总结

当前 PaperPilot 已经完成了很多我之前期待的改造：

```text
Sidebar 基本导航化
TopBar 接近目标 UI
RunIntakeDrawer 已有
ActionApproval 接真实 actions
CodeEditor 使用 Monaco
DiffViewer 使用真实 diff viewer
Files API 使用 run_id
LLM key 不落盘
Productize issues 可从 run result 生成
RunService 有 JSON state
```

但仍然有几个真实问题需要修：

```text
requirements.txt / ci.yml 格式
WebSocket 不是真实时流
Patch direct apply 绕过 approval
Patch syntax result 不够结构化
Inspector/Runner/ToolCall 仍有 mock-era 类型和 fallback
Productize revision buttons 未完全接后端 graph rerun
Graph events 仍有 legacy message fallback
Files workspace 还不是严格统一 run directory
```

下一步不要大改架构，集中修这些闭环问题。  
修完后，PaperPilot 才能从：

```text
Workbench Preview
```

提升到：

```text
PaperPilot Workbench v1.2：真实可用的 Research Agent IDE
```
