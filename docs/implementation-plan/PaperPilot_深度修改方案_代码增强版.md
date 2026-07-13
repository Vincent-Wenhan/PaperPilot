# PaperPilot 深度修改方案

> **代码增强版（第二轮逐文件复核）**：在原方案基础上新增约 4,500 行逐文件诊断与可直接落地代码，重点补充 Durable Run/Event、SSE token 流、LangGraph interrupt/resume、Docker Sandbox、Next.js Productize、前端 reducer/Store、真实 Preview 与自动化测试。新增内容从“第二轮逐文件复核：代码增强版”开始。

> 仓库：`Vincent-Wenhan/PaperPilot`  
> 审查分支：`master`  
> 审查日期：2026-07-14  
> 目标：把 PaperPilot 从“带流程图的 Agent Demo”升级为真正可持续运行、可恢复、可审查、可交互的论文产品化工作台。

---

## 1. 结论先行

PaperPilot 当前的问题并不只是 UI 不够美观，而是 **产品交互模型、运行状态模型、Agent 执行层和安全边界没有统一**。现有代码已经具备不少可复用模块，例如：

- 论文解析、仓库扫描、结构化 Agent；
- Reproduce / Productize LangGraph；
- 代码质量检查、Patch 审批、命令风险分类；
- Next.js Workbench、Monaco、文件树、流程图和 FastAPI API。

但这些模块被拼接成了一个“看起来在运行”的工作台，而不是一个能够稳定完成任务的 Agent 产品。最核心的症状是：

1. **界面显示的状态不一定等于后端真实状态。**
2. **用户在界面上修改的计划并不会改变后端执行。**
3. **WebSocket 只发送阶段事件，没有真实的模型输出流。**
4. **刷新页面后，等待审核或已完成的 Run 会被主动清除。**
5. **后端重启后，正在运行的任务直接被标记失败，无法续跑。**
6. **Productize 最终仍主要生成静态 Mock 网页，而不是可迭代、可构建、可运行的真实项目。**
7. **当前“sandbox”不是容器沙箱，而是在宿主机中执行命令。**
8. **LLM API Key 存在明文落盘并返回浏览器的严重安全问题。**

因此，不建议继续在现有 `WorkspaceShell` 和状态推断逻辑上打补丁。更合理的路线是：

> **保留论文解析、Agent、Schema、质量检查和部分 LangGraph 节点；重写 Workbench 状态层、事件协议、运行持久化、沙箱层和主交互界面。**

建议的最终形态是：

```text
Chat-first Workspace
├── 左侧：Project / Thread / Run 历史
├── 中间：对话、Agent 过程、工具调用、审批与结果
├── 右侧：Artifact / Code / Diff / Preview / Trace
└── 底部：Composer、附件、模式、模型、停止与继续

FastAPI Control Plane
├── Run / Thread / Message API
├── Durable Event Store + SSE
├── Plan / Approval / Resume / Cancel
├── Artifact / File / Patch API
└── Preview Proxy

Durable Agent Runtime
├── LangGraph Checkpointer
├── Reproduce Graph
├── Productize Graph
├── Build-Test-Repair Loop
└── Isolated Docker Sandbox
```

---

## 2. 本次代码审查范围

重点审阅了以下实现：

- `frontend/components/workspace-shell.tsx`
- `frontend/lib/api.ts`
- `frontend/stores/workbench-store.ts`
- `frontend/components/layout/*`
- `frontend/components/inspector/*`
- `backend/main.py`
- `backend/routers/runs.py`
- `backend/routers/llm.py`
- `backend/routers/uploads.py`
- `backend/services/run_service.py`
- `backend/services/event_service.py`
- `backend/services/graph_service.py`
- `backend/services/file_service.py`
- `backend/services/patch_service.py`
- `backend/services/command_service.py`
- `tools/llm_client.py`
- `tools/command_runner.py`
- `tools/github_tool.py`
- `agents/base_agent.py`
- `agents/structured_agent.py`
- `graphs/reproduce_graph.py`
- `graphs/productize_graph.py`
- Reproduce / Productize 相关 Agent、Schema 与测试目录。

本报告属于 **关键链路静态代码审查与架构设计**。由于本次环境未完整拉取并启动仓库依赖，没有声称已经在作者本地配置下执行所有测试；文档中把“代码可直接确认的问题”和“需要运行验证的风险”进行了区分。

---

## 3. 当前架构中最严重的问题

## 3.1 P0：LLM API Key 明文落盘并返回前端

### 当前实现

`backend/routers/llm.py`：

- 将配置写入仓库根目录 `llm_config.json`；
- `GET /api/llm/config` 返回完整 `api_key`；
- 前端挂载时把返回的 Key 放进 React state；
- 与 README 中“API keys are not written to repository config files”的描述矛盾。

### 风险

- 浏览器中任何能访问 API 的用户都可能读取 Key；
- Key 会出现在本地备份、同步工具、错误打包或误提交中；
- 前端状态、浏览器扩展和开发者工具都能看到 Key；
- 多用户部署时会共享同一个密钥。

### 修改方案

1. 后端只返回：`configured: true/false`、模型名和 endpoint label；
2. Key 使用环境变量、OS Keyring 或服务端 Secret Store；
3. 前端永远不回显已有 Key；
4. 保存时只接受新 Key，不提供读取接口；
5. 增加配置所属用户或 workspace。

### 核心代码

```python
# backend/routers/llm.py
from pydantic import BaseModel, SecretStr
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/llm", tags=["llm"])

class LLMConfigView(BaseModel):
    configured: bool
    base_url: str
    model: str
    implementation_model: str

class LLMConfigUpdate(BaseModel):
    api_key: SecretStr | None = None
    base_url: str
    model: str
    implementation_model: str = ""

@router.get("/config", response_model=LLMConfigView)
def get_llm_config(
    secrets: "SecretStore" = Depends(get_secret_store),
) -> LLMConfigView:
    config = secrets.get_llm_config()
    return LLMConfigView(
        configured=bool(config.api_key),
        base_url=config.base_url,
        model=config.model,
        implementation_model=config.implementation_model,
    )

@router.put("/config", response_model=LLMConfigView)
def update_llm_config(
    body: LLMConfigUpdate,
    secrets: "SecretStore" = Depends(get_secret_store),
) -> LLMConfigView:
    secrets.update_llm_config(
        api_key=body.api_key.get_secret_value() if body.api_key else None,
        base_url=body.base_url,
        model=body.model,
        implementation_model=body.implementation_model,
    )
    return get_llm_config(secrets)
```

开发模式可先使用 `.env.local`；正式部署建议接入系统 Keyring、Docker Secret、Kubernetes Secret 或云 Secret Manager。

---

## 3.2 P0：当前 Sandbox 并不是真正的沙箱

### 当前实现

`tools/command_runner.py` 中的 `run_command_sandbox()`：

1. 把工作目录复制到 `workspace/sandboxes/...`；
2. 使用 `subprocess.run()` 在宿主机执行；
3. 没有容器、用户命名空间、网络隔离、文件系统隔离、CPU/内存限制；
4. 临时目录不会自动删除；
5. `review` 模式对通过简单字符串规则的命令可直接在宿主机执行。

“复制到临时目录”只能避免直接覆盖原文件，**不能防止恶意代码读取环境变量、访问网络、扫描宿主机或消耗资源**。

### 修改方案

使用 Docker/Podman runner，最少满足：

- 非 root 用户；
- `cap_drop=ALL`；
- 默认禁用网络；
- 只挂载当前 Run 的 workspace；
- 只读 root filesystem；
- CPU、内存、PID、输出和执行时间限制；
- 不传入宿主机 LLM Key；
- 每个 Run 使用独立容器和独立目录；
- 完成后销毁容器。

### 核心代码

```python
# backend/runtime/docker_runner.py
from pathlib import Path
import docker

class DockerRunner:
    def __init__(self) -> None:
        self.client = docker.from_env()

    def run(
        self,
        *,
        workspace: Path,
        command: list[str],
        image: str = "paperpilot-runner:py312-node20",
        timeout_s: int = 600,
        network_enabled: bool = False,
    ) -> dict:
        workspace = workspace.resolve(strict=True)

        container = self.client.containers.run(
            image=image,
            command=command,
            working_dir="/workspace",
            volumes={
                str(workspace): {"bind": "/workspace", "mode": "rw"},
            },
            user="1000:1000",
            detach=True,
            network_disabled=not network_enabled,
            read_only=True,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            mem_limit="4g",
            nano_cpus=2_000_000_000,
            pids_limit=256,
            tmpfs={"/tmp": "rw,noexec,nosuid,size=512m"},
            environment={
                "HOME": "/tmp/home",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            },
        )

        try:
            result = container.wait(timeout=timeout_s)
            stdout = container.logs(stdout=True, stderr=False).decode(
                "utf-8", errors="replace"
            )
            stderr = container.logs(stdout=False, stderr=True).decode(
                "utf-8", errors="replace"
            )
            return {
                "exit_code": result.get("StatusCode"),
                "stdout": stdout[-100_000:],
                "stderr": stderr[-100_000:],
            }
        finally:
            container.remove(force=True)
```

依赖安装需要联网时，不能简单长期开放外网。建议拆成：

```text
resolve dependencies → 审核锁文件 → 临时允许包源 → 构建镜像层
                                      ↓
                           执行阶段默认断网
```

---

## 3.3 P0：界面上的“编辑计划”是假的

### 当前实现

在 `WorkspaceShell` 中：

```ts
function togglePlanStep(stepId: string) {
  setPlanState(...); // 只改前端本地 state
}

function approvePlan() {
  setNotice("Plan review acknowledged...");
  addTimelineEvent("Editable plan review acknowledged.");
}
```

它没有：

- 调用后端修改 Run Plan；
- 改变 LangGraph state；
- 禁用任何 Agent 节点；
- 触发 resume；
- 进行 plan version 冲突检查。

用户以为已经删除或关闭步骤，后端仍执行原始流程。这是明显的交互欺骗和功能 Bug。

### 修改方案

计划必须是后端持久化的一等实体：

```text
Plan
├── version
├── steps[]
│   ├── id
│   ├── title
│   ├── agent
│   ├── enabled
│   ├── dependencies
│   ├── approval_required
│   └── config
└── status: draft / approved / superseded
```

后端使用乐观锁更新，并在用户批准后从 LangGraph interrupt 继续。

### 后端核心代码

```python
class PlanStepUpdate(BaseModel):
    step_id: str
    enabled: bool

class PlanPatch(BaseModel):
    expected_version: int
    changes: list[PlanStepUpdate]

@router.patch("/runs/{run_id}/plan")
def patch_plan(run_id: str, body: PlanPatch) -> PlanView:
    with repository.transaction() as tx:
        plan = tx.get_plan_for_update(run_id)
        if plan.version != body.expected_version:
            raise HTTPException(409, "Plan was updated by another request")

        plan.apply(body.changes)
        plan.version += 1
        tx.save(plan)
        tx.append_event(
            run_id=run_id,
            event_type="plan.updated",
            payload={"version": plan.version, "steps": plan.steps},
        )
        return PlanView.model_validate(plan)

@router.post("/runs/{run_id}/plan/approve")
def approve_plan(run_id: str, body: PlanApproval) -> RunView:
    plan = repository.approve_plan(run_id, body.version)
    runtime.resume(run_id, value={"approved_plan": plan.model_dump()})
    return repository.get_run(run_id)
```

### 前端核心代码

```tsx
const updatePlan = useMutation({
  mutationFn: (changes: PlanStepUpdate[]) =>
    api.patchPlan(runId, {
      expected_version: plan.version,
      changes,
    }),
  onSuccess: (nextPlan) => {
    queryClient.setQueryData(["run-plan", runId], nextPlan);
  },
});
```

---

## 3.4 P0：没有真实的模型流式输出

### 当前实现

- `tools/llm_client.py` 使用同步 `chat.completions.create()`；
- 没有 `stream=True`；
- 后端主要只发送 `node_started`；
- WebSocket 每收到一个事件，就再请求 Run、Graph、Actions、Commands、Result 五个接口；
- 所谓“实时”本质是“收到阶段通知后重新拉取整份状态”。

这会导致：

- 模型长时间生成时界面没有内容；
- 用户感觉卡住；
- 每个事件触发多个请求；
- 请求返回顺序不同可能让旧状态覆盖新状态；
- 无法实现 Stop、Retry、Continue from here。

### 修改方案

采用：

```text
HTTP commands + SSE event stream
```

SSE 更适合 PaperPilot 当前单向服务端推送场景，并天然支持事件 ID、自动重连和 `Last-Event-ID`。交互操作继续使用普通 HTTP。

事件类型建议：

```text
run.created
run.status
node.started
node.progress
node.completed
assistant.message.start
assistant.message.delta
assistant.message.completed
tool.started
tool.output.delta
tool.completed
artifact.created
artifact.updated
approval.required
approval.resolved
run.completed
run.failed
```

### 统一事件 Schema

```python
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

class RunEvent(BaseModel):
    seq: int
    event_id: str
    run_id: str
    thread_id: str
    type: str
    status: Literal[
        "queued", "running", "waiting_input", "waiting_approval",
        "succeeded", "failed", "cancelled"
    ] | None = None
    node_id: str | None = None
    message_id: str | None = None
    artifact_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    schema_version: int = 1
```

### FastAPI SSE 核心代码

```python
import asyncio
import json
from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None),
):
    after_seq = int(last_event_id or 0)

    async def generate():
        nonlocal after_seq
        while not await request.is_disconnected():
            events = await event_repo.list_after(run_id, after_seq, limit=200)
            if events:
                for event in events:
                    after_seq = event.seq
                    yield (
                        f"id: {event.seq}\n"
                        f"event: {event.type}\n"
                        f"data: {event.model_dump_json()}\n\n"
                    )
            else:
                yield ": heartbeat\n\n"
                await asyncio.sleep(10)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
```

### 前端流式 Hook

```tsx
export function useRunStream(runId: string | undefined) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!runId) return;

    const source = new EventSource(
      `${API_BASE}/api/runs/${runId}/events`,
      { withCredentials: true },
    );

    const apply = (raw: MessageEvent) => {
      const event = RunEventSchema.parse(JSON.parse(raw.data));

      queryClient.setQueryData<RunSnapshot>(
        ["run-snapshot", runId],
        (current) => reduceRunEvent(current, event),
      );
    };

    source.onmessage = apply;
    source.addEventListener("assistant.message.delta", apply);
    source.addEventListener("node.progress", apply);
    source.addEventListener("artifact.updated", apply);

    source.onerror = () => {
      // EventSource 会按 Last-Event-ID 自动重连。
      // UI 只显示“正在重连”，不要清空已有状态。
    };

    return () => source.close();
  }, [runId, queryClient]);
}
```

### LLM 流式核心代码

```python
from openai import AsyncOpenAI

class OpenAICompatibleProvider:
    async def stream_text(self, messages, model, **kwargs):
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
```

注意：不要向用户暴露模型私有思维链。UI 可以流式展示“可公开的工作摘要、工具状态和最终内容”，而不是隐藏推理。

---

## 3.5 P0：Run、Event、Result 三套状态源互相不一致

### 当前实现

目前同时存在：

- `InMemoryRunService` 字典；
- `run_state.json`；
- 每个 Run 一个 JSONL Event 文件；
- 进程内 subscriber；
- 前端本地推断的 graph status。

问题包括：

- Event 写入和 Run 状态更新不是同一事务；
- JSONL 并发 append 没有可靠事务边界；
- 多个 Uvicorn worker 各自持有不同内存状态；
- 重启后 `_recover_stale_running_runs()` 直接把运行任务标记失败；
- `_llm_configs` 只在内存中保存；
- `after_id` 指向不存在事件时，当前读取逻辑可能返回空列表；
- WebSocket 重连会重放全部历史事件；
- 前端再根据消息字符串猜测图节点状态。

### 修改方案

使用一个一致的持久化模型：

```text
projects
threads
runs
run_nodes
plans
messages
run_events
artifacts
action_requests
jobs
```

开发模式可用 SQLite WAL；多人或多 worker 部署使用 PostgreSQL。Run 状态变化与 Event append 必须在一个数据库事务中完成。

### SQLAlchemy 模型示意

```python
class RunEventRow(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(index=True)
    event_id: Mapped[str] = mapped_column(unique=True, index=True)
    event_type: Mapped[str] = mapped_column(index=True)
    node_id: Mapped[str | None]
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(primary_key=True)
    thread_id: Mapped[str] = mapped_column(index=True)
    mode: Mapped[str]
    status: Mapped[str] = mapped_column(index=True)
    current_node: Mapped[str | None]
    error_code: Mapped[str | None]
    error_message: Mapped[str | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

```python
def transition_run(
    session: Session,
    *,
    run_id: str,
    status: RunStatus,
    event_type: str,
    payload: dict,
) -> RunEventRow:
    run = session.get(RunRow, run_id, with_for_update=True)
    validate_transition(run.status, status)

    run.status = status
    run.updated_at = utcnow()

    event = RunEventRow(
        run_id=run_id,
        event_id=f"evt_{uuid4().hex}",
        event_type=event_type,
        payload=payload,
    )
    session.add(event)
    session.flush()
    return event
```

---

## 3.6 P0：刷新页面后会丢失等待审核和已完成的 Run

### 当前实现

前端只记住 `status === "running"` 的 Run。恢复时如果状态不是 running，会主动调用 `clearStaleRun()`。

这会直接破坏最重要的 Agent 工作流：

- Productize proposal review；
- 命令审批；
- Patch 审批；
- 查看失败原因；
- 查看生成结果；
- 完成后继续追问。

### 修改方案

Run 应属于 Thread，Thread 永久出现在左侧历史中。页面 URL 必须可恢复：

```text
/projects/{project_id}/threads/{thread_id}?run={run_id}
```

运行状态不应决定是否保存。只需区分：

```text
queued / running / waiting_input / waiting_approval /
succeeded / failed / cancelled
```

前端刷新后从 URL 加载 Thread Snapshot，而不是依赖 sessionStorage。

---

## 3.7 P0：上传接口容易造成内存和磁盘 DoS

### 当前实现

`upload_pdf()`：

- 只检查文件名后缀；
- `await file.read()` 一次性读入全部内存；
- 没有大小限制；
- 没有 PDF magic bytes 或 MIME 验证；
- 没有按用户和项目隔离；
- 没有过期清理；
- 返回服务器绝对路径。

### 修改方案与核心代码

```python
MAX_PDF_BYTES = 100 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024

@router.post("/projects/{project_id}/files")
async def upload_pdf(project_id: str, file: UploadFile):
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(415, "Unsupported media type")

    file_id = f"file_{uuid4().hex}"
    dest = storage.project_file_path(project_id, file_id, suffix=".pdf")
    size = 0
    first_chunk = True

    async with aiofiles.open(dest, "wb") as output:
        while chunk := await file.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "PDF is too large")
            if first_chunk:
                first_chunk = False
                if not chunk.startswith(b"%PDF-"):
                    dest.unlink(missing_ok=True)
                    raise HTTPException(400, "Invalid PDF signature")
            await output.write(chunk)

    return {"file_id": file_id, "name": file.filename, "size": size}
```

后续 API 只传 `file_id`，不要让前端知道服务器绝对路径。

---

## 3.8 P1：前端 `WorkspaceShell` 已经成为 God Component

`WorkspaceShell` 同时负责：

- 配置加载；
- 文件上传；
- Run 创建与恢复；
- WebSocket 生命周期；
- 轮询和状态合并；
- Graph 状态推断；
- Action 审批；
- Product proposal 执行；
- Revision；
- 页面导航；
- UI notice；
- Run form；
- 本地 plan；
- result 与 issue 映射。

这会导致任何一处改动都可能影响整个页面。虽然项目安装了 Zustand，但现有 store 只包含硬编码的 run/artifact id，几乎没有承担真实状态管理。

### 修改方案

严格分离三类状态：

```text
Server state  → TanStack Query
Stream state  → run event reducer / query cache
UI state      → Zustand（面板、选中 tab、drawer、宽度）
Form state    → React Hook Form + Zod
```

建议目录：

```text
frontend/
  app/
    (workbench)/projects/[projectId]/threads/[threadId]/page.tsx
  features/
    runs/
      api.ts
      schemas.ts
      use-run.ts
      use-run-stream.ts
      run-reducer.ts
    messages/
    plans/
    approvals/
    artifacts/
    preview/
  components/
    shell/
    chat/
    tools/
    artifacts/
  stores/
    ui-store.ts
```

### UI Store 只保存 UI 状态

```ts
interface WorkbenchUIState {
  rightPanelOpen: boolean;
  rightPanelTab: "artifact" | "code" | "diff" | "preview" | "trace";
  leftSidebarCollapsed: boolean;
  selectedArtifactId?: string;
  setRightPanelTab: (tab: WorkbenchUIState["rightPanelTab"]) => void;
}

export const useWorkbenchUI = create<WorkbenchUIState>((set) => ({
  rightPanelOpen: true,
  rightPanelTab: "artifact",
  leftSidebarCollapsed: false,
  setRightPanelTab: (rightPanelTab) =>
    set({ rightPanelTab, rightPanelOpen: true }),
}));
```

不要把 Run、Messages、Actions 等服务端数据复制到 Zustand。

---

## 3.9 P1：流程图状态通过字符串关键字推断

当前前后端都存在类似逻辑：

```text
message 包含 "evaluation" → evaluation node
message 包含 "prototype" → prototype node
message 包含 "report" → outputs node
```

同时还会把“最新节点之前的 pending/running 节点”直接推断为 success。这样非常容易出现：

- 节点实际上失败却被自动涂成绿色；
- Agent 文案变化后映射失效；
- 并行节点显示顺序错误；
- 重新执行某一节点时旧状态污染新状态。

### 修改方案

每个 runtime node 明确产生：

```json
{
  "type": "node.completed",
  "node_id": "product.evaluate",
  "node_run_id": "nr_123",
  "attempt": 2,
  "status": "succeeded",
  "started_at": "...",
  "finished_at": "..."
}
```

流程图只消费 `run_nodes` 表，不再读自然语言 message。

---

## 3.10 P1：LLM Provider 层过于单一

当前 `LLMClient` 只围绕 OpenAI-compatible Chat Completions 设计：

- provider 能力靠模型名前缀判断；
- 不支持统一的流式事件；
- 不记录 token、费用、latency；
- 没有按 stage 设置预算；
- base URL 可由前端任意传入，存在 SSRF 风险；
- timeout 与多层 retry 可能让失败等待很久；
- structured output 失败后只再提示一次。

### 修改方案

引入 Provider Adapter：

```python
class ModelCapabilities(BaseModel):
    streaming: bool
    json_schema: bool
    tool_calling: bool
    vision: bool
    max_context_tokens: int

class ModelProvider(Protocol):
    capabilities: ModelCapabilities

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]: ...
    async def generate_object(self, request: ObjectRequest) -> BaseModel: ...
```

对 base URL：

- 单用户本地版可以允许自定义；
- 服务端部署必须使用 provider allowlist；
- 拒绝 localhost、metadata IP、内网地址及非 HTTPS 地址；
- 或把自定义模型配置限制在管理员侧。

```python
BLOCKED_NETS = [
    ip_network("127.0.0.0/8"),
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("169.254.0.0/16"),
]
```

---

## 4. Agent 能力为什么没有达到预期

## 4.1 Reproduce 的问题

当前 Reproduce 已有结构化理解、计划、实现、Review、Sandbox Verify 和 Diagnosis，但仍容易产出“看似完整、无法真正复现”的代码，原因主要是：

1. 仓库分析偏浅，缺少符号、调用图、配置和数据流索引；
2. 在有官方仓库时，仍容易生成一个独立的通用小项目，而不是围绕原仓库做最小可运行改造；
3. 代码生成与真实环境验证之间反馈信息不够结构化；
4. 缺少可恢复的多轮 Build-Test-Fix；
5. 验证偏语法、文件完整度和 smoke test，不足以证明数据、模型与命令链路可执行；
6. 对模型权重、数据集、硬件和缺失依赖没有形成明确的 blocker；
7. 用户看不到“哪些内容来自论文、哪些来自仓库、哪些是 Agent 推断”。

### 建议的新链路

```text
Evidence Ingestion
  ├── PDF section / table / equation index
  ├── Repo tree / symbols / entrypoints / config index
  └── Evidence citations
        ↓
Execution Contract
  ├── target task
  ├── exact entrypoint
  ├── inputs / outputs
  ├── environment
  ├── checkpoint / dataset blockers
  └── acceptance tests
        ↓
Implementation Strategy
  ├── use official repo directly
  ├── patch official repo in worktree
  └── create isolated minimal project only when no repo exists
        ↓
Build → Test → Diagnose → Minimal Patch（最多 3 轮）
        ↓
Reproduction Report + Remaining Blockers
```

### Repo 索引结构

```python
class RepositoryIndex(BaseModel):
    files: list[FileSummary]
    symbols: list[Symbol]
    imports: list[ImportEdge]
    entrypoints: list[Entrypoint]
    configs: list[ConfigReference]
    dataset_loaders: list[SymbolRef]
    model_builders: list[SymbolRef]
    checkpoint_loaders: list[SymbolRef]
    cli_arguments: list[CLIArgument]
    evidence: list[CodeEvidence]
```

可以使用 `ripgrep + tree-sitter + AST` 做静态索引，而不是把大量源码直接塞给 LLM。

### Build-Test-Repair Loop

```python
MAX_REPAIR_ATTEMPTS = 3

for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
    result = await sandbox.run(test_plan.commands)
    await events.emit_test_result(run_id, attempt, result)

    if result.acceptance_passed:
        break

    if attempt == MAX_REPAIR_ATTEMPTS:
        raise VerificationFailed(result.failures)

    patch = await repair_agent.run(
        contract=contract,
        changed_files=workspace.changed_files(),
        failures=result.failures,
        logs=result.relevant_logs,
    )
    await patch_service.propose_and_apply_internal(patch)
```

重点是把失败反馈限制为：

- 相关文件；
- 编译器或测试错误；
- 当前 contract；
- 最近一次 patch；

而不是每轮重新让模型生成整个项目。

---

## 4.2 Productize 的问题

README 和代码都表明当前 Productize 的主要交付仍是：

```text
index.html
app.js
adapter.js
styles.css
README.md
product_spec.md
```

并且 `adapter.js` 默认 Mock。这对早期概念展示有价值，但无法满足“把论文方法变成真实可用产品”的目标。

### 根本矛盾

当前 Productize 同时想做：

- idea generation；
- PRD；
- UI 设计；
- 真实代码；
- 模型适配；
- 验证。

但执行器最终只输出静态 bundle，因此前面的 PRD、架构和评估很难真正约束工程实现。

### 建议改成三级交付

```text
Level 1 — Clickable Mock
用于验证 JTBD、页面和交互，不宣称真实能力。

Level 2 — Functional App
真实 Next.js 项目、持久状态、Mock adapter、可构建、可预览。

Level 3 — Model-integrated App
接入论文代码/模型服务，拥有真实输入输出和端到端验证。
```

用户创建 Run 时明确选择目标层级，避免静态 Mock 被误认为真实产品。

### Functional App 最低合同

```python
class ProductBuildContract(BaseModel):
    framework: Literal["nextjs"] = "nextjs"
    package_manager: Literal["pnpm"] = "pnpm"
    required_routes: list[str]
    required_components: list[str]
    required_user_flows: list[UserFlow]
    adapter_interface: AdapterContract
    persistence: Literal["none", "sqlite", "postgres"]
    auth: Literal["none", "local", "oauth"]
    build_command: str = "pnpm build"
    test_command: str = "pnpm test"
    preview_command: str = "pnpm dev --hostname 0.0.0.0"
```

### 生成目录

```text
generated_product/
  app/
  components/
  features/
  lib/
    adapters/
      contract.ts
      mock-adapter.ts
      real-adapter.ts
  tests/
  public/
  package.json
  next.config.ts
  README.md
  product-spec.md
```

### Adapter 边界

```ts
export interface PaperCapabilityAdapter {
  analyze(input: AnalyzeInput, signal?: AbortSignal): Promise<AnalyzeResult>;
  health(): Promise<{ ok: boolean; detail?: string }>;
}

export class MockAdapter implements PaperCapabilityAdapter {
  async analyze(input: AnalyzeInput): Promise<AnalyzeResult> {
    return loadFixtureFor(input);
  }
}

export class HttpModelAdapter implements PaperCapabilityAdapter {
  constructor(private readonly endpoint: string) {}

  async analyze(input: AnalyzeInput, signal?: AbortSignal) {
    const response = await fetch(`${this.endpoint}/analyze`, {
      method: "POST",
      body: JSON.stringify(input),
      headers: { "Content-Type": "application/json" },
      signal,
    });
    if (!response.ok) throw new Error(await response.text());
    return AnalyzeResultSchema.parse(await response.json());
  }
}
```

这样即使首轮使用 Mock，产品结构也是真实可替换的，而不是把 Mock 逻辑散落在界面中。

---

## 5. 推荐的新 UI 与交互模型

## 5.1 不要把流程图作为主界面

当前界面更像 DevOps Dashboard：大量面板、节点、状态和日志。它适合调试，但不适合作为普通用户的主入口。

ChatGPT、Claude 和 Codex 类产品的共同点并不只是“圆角和黑白配色”，而是：

- 用户任务始终位于中心；
- Agent 过程按时间自然展开；
- 工具调用嵌在上下文中；
- 复杂细节默认折叠；
- 产物在侧边可持续编辑；
- 用户随时可打断、纠正、继续；
- 历史会话和当前任务可恢复。

### 推荐布局

```text
┌──────────────────────────────────────────────────────────────────┐
│ PaperPilot   Project / Thread                    Model   ···      │
├──────────────┬──────────────────────────────┬────────────────────┤
│ Projects     │ Conversation / Run Timeline  │ Artifact Workspace │
│              │                              │                    │
│ + New task   │ User message                 │ Preview            │
│ Today        │ Assistant summary            │ Code               │
│  Thread A    │ ┌ Tool call: Parse PDF ┐     │ Diff               │
│  Thread B    │ └ Completed            ┘     │ Files              │
│ Previous     │ ┌ Approval required    ┐     │ Trace              │
│              │ └ Review / Reject      ┘     │                    │
│              │                              │                    │
│              │ [ composer + attachments ]   │                    │
└──────────────┴──────────────────────────────┴────────────────────┘
```

### 主界面只保留三层信息

1. **对话层**：用户真正关心的结论、问题和可操作项；
2. **过程层**：工具调用、节点摘要、审批和错误，默认折叠；
3. **调试层**：完整 graph、原始 logs、payload，在 Trace Tab 中查看。

---

## 5.2 Message Part 模型

不要再把所有内容变成 timeline string。使用结构化 message parts：

```ts
type MessagePart =
  | { type: "text"; text: string }
  | { type: "status"; label: string; status: RunStatus }
  | { type: "tool"; toolCall: ToolCallView }
  | { type: "approval"; action: ApprovalView }
  | { type: "artifact"; artifact: ArtifactRef }
  | { type: "sources"; sources: EvidenceRef[] }
  | { type: "error"; error: UserFacingError };
```

### Tool Card

```tsx
function ToolCallCard({ call }: { call: ToolCallView }) {
  return (
    <Collapsible defaultOpen={call.status === "running"}>
      <CollapsibleTrigger className="tool-card-trigger">
        <ToolIcon name={call.tool} />
        <span>{call.title}</span>
        <StatusBadge status={call.status} />
        <Duration value={call.durationMs} />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ToolSummary summary={call.summary} />
        {call.logs && <LogViewer value={call.logs} />}
      </CollapsibleContent>
    </Collapsible>
  );
}
```

---

## 5.3 审批应嵌入对话，而不是常驻大抽屉

审批卡应清楚展示：

- Agent 想做什么；
- 为什么要做；
- 风险等级；
- 将影响哪些文件；
- 命令或 Diff；
- 预期结果；
- Approve once / Always allow this rule / Reject / Edit。

```tsx
<ApprovalCard
  title="Run smoke test"
  risk="medium"
  reason="Verify the generated app before marking the run complete."
  command="pnpm test"
  cwd="generated_product/app"
  onApprove={() => approve(action.id)}
  onEdit={() => openEditor(action.id)}
  onReject={() => reject(action.id)}
/>
```

对 Patch 必须默认显示 diff，而不是只显示路径。

---

## 5.4 Composer 设计

底部输入框建议包含：

```text
[+] 附件   [Reproduce ▾]   输入任务……             [Model ▾] [Send]
```

运行中变为：

```text
[+] 附件   输入补充指令……              [Stop] [Send instruction]
```

支持：

- PDF、Repo URL、图片和文本附件；
- `@paper`、`@repo`、`@artifact` 上下文引用；
- `/plan`、`/retry`、`/stop` 等命令；
- Shift+Enter 换行；
- 拖拽上传；
- 运行中追加用户指令；
- 失败后“一键将错误交给 Agent 修复”。

---

## 5.5 视觉系统

建议采用克制的 Linear / ChatGPT 风格，而不是堆叠渐变和大面积卡片。

### Design Tokens

```css
:root {
  --bg: 0 0% 100%;
  --surface: 0 0% 98.5%;
  --surface-raised: 0 0% 100%;
  --border: 220 13% 91%;
  --text: 222 22% 12%;
  --muted: 220 8% 46%;
  --accent: 222 89% 55%;
  --danger: 0 72% 51%;
  --success: 152 60% 36%;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --shadow-panel: 0 1px 2px rgb(0 0 0 / 0.04),
                  0 8px 24px rgb(0 0 0 / 0.05);
}
```

### 原则

- 主背景白色；
- 面板靠边框、层级和留白区分，不依赖重阴影；
- 主内容最大宽度约 820–920px；
- Tool card 使用浅灰背景；
- 状态颜色只用于小图标或 badge；
- 动画 120–180ms；
- 避免所有元素同时动画；
- 右侧面板可拖拽调整并一键折叠；
- 支持浅色和深色，但先把浅色做完整。

---

## 6. 后端目标架构

## 6.1 Control Plane 与 Execution Plane 分离

```text
FastAPI Control Plane
  ├── 用户请求、鉴权、Run API
  ├── SSE、审批、消息、Artifact
  └── 创建 durable job

Agent Worker
  ├── 获取 job lease
  ├── 加载 LangGraph checkpoint
  ├── 执行节点
  ├── 写 event / artifact
  └── heartbeat / cancel check

Sandbox Worker
  ├── Docker build/test/preview
  └── 与 Control Plane 不共享密钥
```

即使 MVP 仍部署在一台机器，也应该是两个进程，而不是 FastAPI 请求进程内 `ThreadPoolExecutor(max_workers=2)`。

---

## 6.2 Durable Job Worker

不一定要立即上 Celery。可以先实现轻量数据库租约 worker：

```python
async def claim_next_job(session: AsyncSession, worker_id: str):
    result = await session.execute(
        select(JobRow)
        .where(JobRow.status == "queued")
        .order_by(JobRow.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if not job:
        return None

    job.status = "running"
    job.worker_id = worker_id
    job.lease_expires_at = utcnow() + timedelta(seconds=60)
    await session.commit()
    return job
```

Worker 定期续租；进程崩溃后 lease 到期，其他 worker 可重新加载 checkpoint 继续。

---

## 6.3 真正使用 LangGraph Checkpointer

当前 graph builder 已预留 `checkpointer` 和 `interrupt_after` 参数，但主 RunService 并没有把它们变成可恢复的工作流。

建议：

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver(pool)
graph = build_productize_graph(
    dependencies,
    checkpointer=checkpointer,
)

config = {
    "configurable": {
        "thread_id": run_id,
        "checkpoint_ns": "productize",
    }
}

await graph.ainvoke(initial_state, config=config)
```

审批节点使用 LangGraph interrupt，而不是“先结束 pipeline，之后再手动拼第二段调用”。

```python
from langgraph.types import interrupt, Command

def approval_node(state):
    decision = interrupt({
        "type": "approval",
        "actions": state["pending_actions"],
    })
    return {"approval_decision": decision}

# 用户批准后
await graph.ainvoke(
    Command(resume={"approved_action_ids": approved_ids}),
    config=config,
)
```

---

## 6.4 Cancel、Retry 与 Branch

必须增加：

```text
POST /runs/{id}/cancel
POST /runs/{id}/retry
POST /runs/{id}/resume
POST /threads/{id}/branch
```

每个较长步骤应在以下位置检查取消标志：

- 模型流的每个 chunk；
- Sandbox 子进程等待循环；
- 多论文循环；
- Build-Test-Repair 每一轮；
- 文件生成批次之间。

```python
async def ensure_not_cancelled(run_id: str):
    if await run_repo.is_cancel_requested(run_id):
        raise RunCancelled(run_id)
```

---

## 7. Artifact、代码和预览链路

## 7.1 Artifact 应是一等实体

不要只在 result 大 JSON 中塞所有内容。

```python
class Artifact(BaseModel):
    id: str
    run_id: str
    kind: Literal[
        "paper_summary", "capability_card", "prd", "plan",
        "code", "diff", "report", "preview", "evaluation"
    ]
    title: str
    version: int
    mime_type: str
    storage_uri: str
    metadata: dict
    created_at: datetime
    updated_at: datetime
```

好处：

- 可单独刷新；
- 可版本化；
- 可评论和修改；
- 可在对话中引用；
- 可显示“本次 Agent 改了哪些内容”。

---

## 7.2 Live Preview

当前静态 `index.html` 预览不能代表真实 Next.js 项目状态。建议：

1. 生成项目后启动 Preview Container；
2. 分配随机内部端口；
3. 后端代理 `/api/previews/{preview_id}/{path}`；
4. iframe 只访问同源 proxy；
5. build error 直接流式展示到对话和 Preview error overlay；
6. 文件修改后触发 HMR。

### Preview Registry

```python
class PreviewSession(BaseModel):
    id: str
    run_id: str
    container_id: str
    internal_port: int
    status: Literal["starting", "ready", "failed", "stopped"]
    expires_at: datetime
```

### 安全要求

- Preview 不可访问控制面内部 API；
- 不注入 LLM Key；
- iframe 使用 CSP 和 sandbox 属性；
- 限制并发 preview 数量；
- 空闲超时自动停止。

```tsx
<iframe
  src={`/api/previews/${previewId}/`}
  sandbox="allow-scripts allow-forms allow-same-origin"
  referrerPolicy="no-referrer"
/>
```

---

## 8. 错误处理与可观测性

当前很多地方使用宽泛 `except Exception`，最终只把字符串塞进 event。建议定义稳定错误码：

```text
PDF_INVALID
PDF_PARSE_FAILED
REPO_CLONE_FAILED
MODEL_AUTH_FAILED
MODEL_RATE_LIMITED
MODEL_OUTPUT_INVALID
PLAN_REJECTED
SANDBOX_TIMEOUT
BUILD_FAILED
TEST_FAILED
PREVIEW_START_FAILED
RUN_CANCELLED
```

### 用户错误与内部错误分开

```python
class UserFacingError(BaseModel):
    code: str
    title: str
    message: str
    recoverable: bool
    suggested_actions: list[str]
    trace_id: str
```

前端展示：

```text
Build failed
The generated app has 2 TypeScript errors.
[Ask Agent to fix] [Open logs] [Open affected files]
```

而不是只显示 `Unknown API error`。

### 观测指标

每个 Run 至少记录：

- stage latency；
- LLM latency、tokens、cost；
- retry count；
- output validation failure；
- sandbox duration；
- build/test pass rate；
- user approval wait time；
- cancellation rate；
- run resume success rate。

推荐 OpenTelemetry + Langfuse/LangSmith 二选一，不要在第一阶段同时引入多个 tracing 平台。

---

## 9. 测试策略

仓库现有 Python 测试数量不少，覆盖 Agent、Graph、工具和 Product scaffold，这是值得保留的基础。但仍需要补上真实产品链路测试。

## 9.1 后端契约测试

```python
def test_event_sequence_is_monotonic(): ...
def test_resume_from_last_event_id(): ...
def test_plan_update_changes_runtime_nodes(): ...
def test_restart_resumes_checkpoint(): ...
def test_cancel_stops_sandbox_process(): ...
def test_llm_config_never_returns_secret(): ...
def test_upload_rejects_oversized_file(): ...
def test_private_base_url_is_rejected(): ...
def test_multi_worker_event_delivery(): ...
```

## 9.2 前端测试

使用 Vitest + Testing Library：

```text
- stream delta 正确合并到同一条消息；
- 重复 event 不会重复渲染；
- out-of-order event 不会回滚状态；
- waiting_approval 刷新后仍能恢复；
- plan 修改失败时回滚 optimistic update；
- Stop 后 composer 状态正确；
- Artifact version 更新后右侧面板刷新。
```

## 9.3 Playwright E2E

最少覆盖四条黄金路径：

```text
1. 上传 PDF → Reproduce → 生成计划 → 批准 → 构建 → 完成
2. Productize → 三个 proposal → 选择一个 → 预览 → 修改 → HMR
3. 运行中刷新页面 → 自动恢复 → 继续收到事件
4. Build 失败 → 打开日志 → Agent 修复 → 测试通过
```

## 9.4 Chaos Test

必须模拟：

- Worker 在 LLM 调用后、写 artifact 前崩溃；
- FastAPI 重启；
- SSE 断线重连；
- 重复提交 approve；
- 用户双击创建 Run；
- Sandbox timeout；
- 数据库暂时不可用。

创建 Run、批准 Action 和执行 Proposal 都应支持 `Idempotency-Key`。

---

## 10. 分阶段实施路线

## Phase 0：止血与真实性修复

目标：不改变整体产品形态，先消除安全问题和“假交互”。

- 删除 API Key GET 回显与明文仓库落盘；
- 上传大小、签名与隔离；
- UI 明确标记 Mock / Real；
- Plan 编辑接入真实后端，或暂时移除编辑开关；
- waiting_review / completed Run 刷新后可恢复；
- 给 Event 增加 `seq`；
- 去掉按 message 文案推断 node 的逻辑；
- 禁止宿主机 review command，未完成 Docker 前只允许精确 allowlist；
- 增加取消 Run；
- 修复前端每个事件触发五次整量请求的问题。

**验收标准：** 用户看到的每个状态都能在后端找到对应事实；页面刷新不会丢任务；任何密钥不会通过 GET 返回。

## Phase 1：重建实时状态层

- SQLite/Postgres 持久化；
- Run / Message / Event / Artifact 表；
- SSE + Last-Event-ID；
- TanStack Query；
- 拆分 `WorkspaceShell`；
- LangGraph checkpointer；
- Durable worker；
- Stop / Resume / Retry。

**验收标准：** 进程重启后 Run 能从 checkpoint 恢复；断线后事件不重不漏；前端不再依赖轮询拼状态。

## Phase 2：Chat-first UI

- Thread 历史；
- Message parts；
- Inline tool / approval；
- 右侧 Artifact workspace；
- Composer；
- Command palette；
- 响应式与可访问性；
- Graph 移入 Trace 调试页。

**验收标准：** 用户不看流程图也能完成完整任务；高级调试信息仍可展开查看。

## Phase 3：真实代码与预览能力

- Docker sandbox；
- Next.js functional generator；
- Build-Test-Repair；
- Preview container + proxy + HMR；
- Repo symbol index；
- Evidence-grounded implementation；
- Model adapter integration。

**验收标准：** Productize 生成的项目能安装、构建、测试和实时预览；Reproduce 能明确区分“验证通过”和“因数据/权重缺失无法验证”。

---

## 11. 建议保留、重写和删除的模块

| 模块 | 建议 | 说明 |
|---|---|---|
| `agents/*` | 保留并重构接口 | 已有结构化 Agent 资产有价值 |
| `schemas/*` | 保留 | 增加版本与 evidence 字段 |
| `graphs/*` | 保留图逻辑，重接 runtime | 真正接入 checkpointer / interrupt |
| `tools/pdf_*` | 保留 | 增加 file_id 和资源限制 |
| `tools/repo_*` | 增强 | 增加 symbol/config/data-flow index |
| `tools/code_quality.py` | 保留 | 接入真实 build/test gate |
| `backend/services/run_service.py` | 重写 | 当前 2000 行级内存服务职责过重 |
| `backend/services/event_service.py` | 重写 | JSONL + 内存 subscriber 不适合作为真相源 |
| `backend/services/graph_service.py` | 大幅简化 | 不再通过文案和顺序推断成功状态 |
| `tools/command_runner.py` | 重写执行层 | 风险分类可保留，执行改 Docker |
| `frontend/components/workspace-shell.tsx` | 拆除重构 | God Component |
| `frontend/stores/workbench-store.ts` | 删除重建 | 当前硬编码且未承担真实职责 |
| 静态 Product scaffold | 保留为 Level 1 | 不再作为默认最终产品 |
| Mock data silent fallback | 删除 | Mock 必须显式显示 |

---

## 12. 推荐参考的开源项目

## 12.1 assistant-ui

适合参考：

- Thread、Message、Composer primitives；
- streaming、auto-scroll、retry、attachment；
- tool call UI；
- shadcn 风格的可组合组件。

建议借鉴组件模型，不要直接复制整套视觉。

## 12.2 Vercel Chatbot / AI SDK

适合参考：

- Next.js App Router 中的聊天数据流；
- message parts；
- SSE stream protocol；
- structured tool data；
- artifacts 与持久化模式。

PaperPilot 后端仍可保留 FastAPI，只需实现兼容或类似的 SSE message protocol。

## 12.3 OpenHands / Agent Canvas

适合参考：

- Conversation 与 Workspace 双区布局；
- Agent action、终端和文件改动的组织；
- 本地/远程 agent server 分离；
- Sandbox 与工作目录边界。

不要直接照搬其复杂后端，PaperPilot 当前规模更适合小型 control plane + worker。

## 12.4 LangGraph 官方持久化与 HITL

当前项目已经使用 LangGraph，最值得做的不是换框架，而是把已经存在的：

- checkpointer；
- interrupt；
- resume；
- stateful execution；

真正接入 Workbench。

---

## 13. 最终建议

PaperPilot 下一版不应继续把“增加更多面板、更多状态 Badge、更多 Agent”作为重点。真正应该解决的是以下四个核心承诺：

### 承诺一：真实

界面中的每一个完成、失败、等待和进度，都由后端结构化事件驱动，不能由前端猜测。

### 承诺二：可恢复

刷新、断网或后端重启后，用户仍能回到原 Thread，并从 checkpoint 继续。

### 承诺三：可执行

生成代码必须经过隔离环境中的 install、build、test、run；Mock 与真实集成必须明确区分。

### 承诺四：可协作

用户可以像使用 ChatGPT、Claude 或 Codex 一样，在任务过程中补充要求、修改计划、批准操作、查看 Diff、继续追问，而不是只能看一个自动播放的流程图。

最推荐的重构优先级是：

```text
密钥与沙箱安全
    ↓
真实 Plan / Run 状态
    ↓
持久化 + SSE + Checkpoint
    ↓
Chat-first UI
    ↓
Build-Test-Repair + Live Preview
```

只要前两层没有解决，再精致的 UI 也会继续给用户“看起来高级，但实际不可靠”的感觉。反过来，当状态、恢复和执行链路真实可靠后，简洁的对话式 UI 就足以显著提升产品质感。

---

## 附录 A：推荐 API 草案

```text
POST   /api/projects
GET    /api/projects

POST   /api/projects/{project_id}/threads
GET    /api/projects/{project_id}/threads
GET    /api/threads/{thread_id}
POST   /api/threads/{thread_id}/messages
POST   /api/threads/{thread_id}/branch

POST   /api/threads/{thread_id}/runs
GET    /api/runs/{run_id}
POST   /api/runs/{run_id}/cancel
POST   /api/runs/{run_id}/retry
POST   /api/runs/{run_id}/resume
GET    /api/runs/{run_id}/events

GET    /api/runs/{run_id}/plan
PATCH  /api/runs/{run_id}/plan
POST   /api/runs/{run_id}/plan/approve

GET    /api/runs/{run_id}/actions
POST   /api/actions/{action_id}/approve
POST   /api/actions/{action_id}/reject
PATCH  /api/actions/{action_id}

GET    /api/runs/{run_id}/artifacts
GET    /api/artifacts/{artifact_id}
GET    /api/artifacts/{artifact_id}/versions
PATCH  /api/artifacts/{artifact_id}

POST   /api/projects/{project_id}/files
GET    /api/projects/{project_id}/files

POST   /api/runs/{run_id}/previews
DELETE /api/previews/{preview_id}
ANY    /api/previews/{preview_id}/{path:path}
```

## 附录 B：Run 状态机

```text
queued
  ├── running
  ├── cancelled
  └── failed

running
  ├── waiting_input
  ├── waiting_approval
  ├── succeeded
  ├── failed
  └── cancelled

waiting_input / waiting_approval
  ├── running
  ├── failed
  └── cancelled

failed
  └── queued (retry creates a new attempt)
```

禁止任意状态跳转；每次 transition 必须生成 event。

## 附录 C：第一批应直接创建的 Issue

1. `security: stop returning and persisting plaintext LLM API keys`
2. `security: replace host subprocess sandbox with container isolation`
3. `bug: plan toggles and approval do not affect backend execution`
4. `bug: preserve waiting-review and completed runs across refresh`
5. `architecture: replace JSONL/in-memory state with durable run store`
6. `streaming: add sequenced SSE event protocol`
7. `frontend: split WorkspaceShell into feature modules`
8. `runtime: connect LangGraph checkpointer and interrupts`
9. `productize: generate buildable Next.js functional app`
10. `preview: add isolated live preview container and proxy`
11. `reproduce: add repository symbol and entrypoint index`
12. `quality: add build-test-repair loop and acceptance tests`
13. `security: add upload size, magic-byte and quota validation`
14. `observability: add trace id, token usage and stage latency`
15. `e2e: add refresh/reconnect/restart/approval Playwright tests`

---

# 第二轮逐文件复核：代码增强版

> 本节是在第一版方案基础上，对当前 `master` 分支的核心实现再次逐文件核对后补充的。重点不再是概念性建议，而是说明：**当前代码具体在哪里断裂、应该替换哪些类和函数、推荐的新代码如何组织、第一批 PR 可以直接写成什么样。**

## D.1 本轮重点复核的真实文件

| 当前文件 | 本轮重点核对内容 | 结论 |
|---|---|---|
| `backend/services/run_service.py` | Run 生命周期、状态持久化、线程池、恢复逻辑、Action 执行 | 运行状态仍由单进程内存对象主导；重启会把运行中任务标记失败；职责严重过载 |
| `backend/services/event_service.py` | JSONL 持久化、订阅、历史重放 | 适合本地 Demo，不适合作为一致性事件源；缺少单调序号、游标与事务边界 |
| `backend/services/graph_service.py` | 节点状态计算、事件到节点映射 | 大量依赖消息关键词和线性“向前补成功”逻辑，不能代表真实 Graph 状态 |
| `backend/routers/llm.py` | API Key 保存和读取 | 完整密钥仍写入 `llm_config.json`，GET 仍会返回完整值 |
| `backend/main.py` | WebSocket 重放与订阅 | 能推事件，但缺少持久游标、断线续传协议、心跳与慢消费者处理 |
| `graphs/reproduce_graph.py` | 计划、命令审批、代码生成、验证修复 | 风险路由只生成“未执行摘要”，三个分支随后都进入代码生成，审批未真正控制 Graph |
| `graphs/productize_graph.py` | Productize 修订、脚手架与最终评估 | 路由仍含固定分数与关键词判断，最终脚手架评估后缺少真正的 Build-Test-Repair 闭环 |
| `runtime/routing.py` | 条件路由 | `ui/adapter/mock/syntax/readme/prototype` 等关键词直接决定修订节点，鲁棒性不足 |
| `pipeline/graph_checkpointer.py` | LangGraph checkpoint | 使用进程内 `InMemorySaver`，服务重启无法恢复 |
| `pipeline/graph_hitl_runner.py` | interrupt/resume | 主要依赖 `interrupt_after` 和多种 resume 输入猜测，没有稳定的 typed resume contract |
| `tools/command_runner.py` | 命令审核与 sandbox | sandbox 只是复制目录后在宿主机 `subprocess.run`；安装依赖也发生在宿主环境 |
| `productize/product_scaffold.py` | 生成产品形态 | 文件头和 README 明确是 deterministic mock-first static prototype |
| `productize/product_tester.py` | 生成结果验证 | 主要做文件存在、字符串 marker、简单括号平衡与 Python AST 检查，未执行真实构建和浏览器测试 |
| `frontend/components/workspace/workspace-shell.tsx` | 主工作台状态与交互 | 1300+ 行 God Component；网络状态、表单、抽屉、编辑器、审批和运行恢复耦合在一起 |
| `frontend/lib/api.ts` | API 类型与请求 | 单文件 500+ 行，运行请求继续携带 `api_key`；缺少按 feature 分层和统一错误模型 |
| `frontend/stores/workbench-store.ts` | Zustand 状态 | 只有 15 行，仅保存两个选中 ID，真实运行状态仍散落在组件 `useState` 中 |

## D.2 当前问题的因果链，而不是孤立 Bug

```text
InMemoryRunService
  + 单 JSON 快照
  + JSONL Event
  + ThreadPoolExecutor
  + InMemorySaver
        ↓
后端没有唯一、可恢复的运行事实源
        ↓
WebSocket 只负责“通知有变化”
        ↓
前端每收到一个事件就重新请求 run/graph/actions/commands/result
        ↓
多个请求返回顺序不确定，旧响应可能覆盖新状态
        ↓
WorkspaceShell 内多个 useEffect / useState 再次派生 UI 状态
        ↓
出现：流式内容不连续、状态闪烁、刷新后丢运行、预览与真实流程不一致
```

所以不建议继续在 `WorkspaceShell` 中加更多 `refreshXxx()` 或定时轮询。正确方向是：

```text
数据库 Run + append-only sequenced Event
                    ↓
            Durable Worker / LangGraph
                    ↓
       SSE 传递增量事件（不是刷新通知）
                    ↓
         前端 reducer 幂等地合并事件
                    ↓
    Query 只做首次快照和断线后的 reconcile
```

---

# E. 后端状态层：可直接替换 `InMemoryRunService` 的实现

## E.1 推荐目录

```text
backend/
├── db/
│   ├── base.py
│   ├── session.py
│   ├── models.py
│   └── migrations/
├── repositories/
│   ├── runs.py
│   ├── events.py
│   ├── actions.py
│   └── artifacts.py
├── services/
│   ├── run_application_service.py
│   ├── event_stream_service.py
│   └── secret_service.py
├── workers/
│   ├── dispatcher.py
│   └── run_worker.py
└── routers/
    ├── runs_v2.py
    └── event_stream.py
```

## E.2 数据模型：不要把所有状态塞进一个 JSON 文件

下面代码可先用 SQLite 开发，生产环境把 URL 换成 PostgreSQL 即可。

```python
# backend/db/models.py
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunModel(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    task: Mapped[str] = mapped_column(Text)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    current_node: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checkpoint_thread_id: Mapped[str] = mapped_column(String(128), unique=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    events: Mapped[list["RunEventModel"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_runs_thread_created", "thread_id", "created_at"),
    )


class RunEventModel(Base):
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    node_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    run: Mapped[RunModel] = relationship(back_populates="events")

    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_event_run_sequence"),
        Index("ix_events_run_sequence", "run_id", "sequence"),
    )


class PlanModel(Base):
    __tablename__ = "run_plans"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    plan_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ActionModel(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    action_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    risk_level: Mapped[str] = mapped_column(String(32))
    request_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(64), index=True)
    logical_path: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str] = mapped_column(String(1024))
    mime_type: Mapped[str] = mapped_column(String(128))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
```

## E.3 事务化事件写入

当前 `_append_event()` 只追加到内存后调用 JSONL 服务，Run 状态更新和 Event 写入不是一个事务。应改为：**状态变化和事件必须同时提交。**

```python
# backend/repositories/events.py
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import RunEventModel, RunModel, utc_now


class EventRepository:
    def append(
        self,
        session: Session,
        *,
        run: RunModel,
        event_type: str,
        payload: dict[str, Any],
        node_id: str | None = None,
        agent_id: str | None = None,
        status: str | None = None,
        message_id: str | None = None,
    ) -> RunEventModel:
        # PostgreSQL 生产环境建议对 run 行 SELECT ... FOR UPDATE，
        # 避免多个 worker 同时拿到相同 sequence。
        session.refresh(run, with_for_update=True)
        next_sequence = run.version + 1
        run.version = next_sequence
        run.updated_at = utc_now()

        event = RunEventModel(
            id=f"evt_{uuid4().hex}",
            run_id=run.id,
            sequence=next_sequence,
            event_type=event_type,
            node_id=node_id,
            agent_id=agent_id,
            status=status,
            message_id=message_id,
            payload=payload,
        )
        session.add(event)
        return event

    def list_after(
        self,
        session: Session,
        *,
        run_id: str,
        after_sequence: int,
        limit: int = 500,
    ) -> Sequence[RunEventModel]:
        stmt = (
            select(RunEventModel)
            .where(
                RunEventModel.run_id == run_id,
                RunEventModel.sequence > after_sequence,
            )
            .order_by(RunEventModel.sequence.asc())
            .limit(limit)
        )
        return session.scalars(stmt).all()
```

## E.4 Run 状态转换必须显式校验

```python
# backend/domain/run_state_machine.py
from __future__ import annotations

from backend.db.models import RunStatus

ALLOWED_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.QUEUED: {
        RunStatus.RUNNING,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    },
    RunStatus.RUNNING: {
        RunStatus.WAITING_INPUT,
        RunStatus.WAITING_APPROVAL,
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.WAITING_INPUT: {
        RunStatus.RUNNING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.WAITING_APPROVAL: {
        RunStatus.RUNNING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.FAILED: set(),
    RunStatus.SUCCEEDED: set(),
    RunStatus.CANCELLED: set(),
}


class InvalidRunTransition(ValueError):
    pass


def assert_transition(current: str, target: str) -> None:
    source = RunStatus(current)
    destination = RunStatus(target)
    if destination not in ALLOWED_TRANSITIONS[source]:
        raise InvalidRunTransition(f"Invalid transition: {source} -> {destination}")
```

```python
# backend/services/run_application_service.py
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import RunModel, RunStatus
from backend.domain.run_state_machine import assert_transition
from backend.repositories.events import EventRepository


class RunApplicationService:
    def __init__(self, event_repository: EventRepository) -> None:
        self.events = event_repository

    def transition(
        self,
        session: Session,
        *,
        run_id: str,
        target: RunStatus,
        event_type: str,
        payload: dict[str, Any],
        node_id: str | None = None,
    ) -> RunModel:
        run = session.scalar(
            select(RunModel).where(RunModel.id == run_id).with_for_update()
        )
        if run is None:
            raise LookupError(f"Run not found: {run_id}")

        assert_transition(run.status, target.value)
        run.status = target.value
        run.current_node = node_id or run.current_node

        self.events.append(
            session,
            run=run,
            event_type=event_type,
            node_id=node_id,
            status=target.value,
            payload=payload,
        )
        session.commit()
        session.refresh(run)
        return run
```

## E.5 创建 Run：请求中不再携带 API Key

```python
# backend/schemas/run_v2.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class RunCreateV2(BaseModel):
    project_id: str = Field(min_length=1, max_length=64)
    thread_id: str = Field(min_length=1, max_length=64)
    mode: Literal["reproduce", "productize"]
    task: str = Field(min_length=1, max_length=20_000)
    file_ids: list[str] = Field(default_factory=list, max_length=10)
    github_url: HttpUrl | None = None
    model_profile_id: str
    options: dict[str, str | int | float | bool] = Field(default_factory=dict)
```

```python
# backend/routers/runs_v2.py
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.db.models import RunModel, RunStatus
from backend.db.session import get_session
from backend.repositories.events import EventRepository
from backend.schemas.run_v2 import RunCreateV2
from backend.workers.dispatcher import dispatcher

router = APIRouter(prefix="/api/v2/runs", tags=["runs-v2"])
events = EventRepository()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_run(
    request: RunCreateV2,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    run_id = f"run_{uuid4().hex}"
    run = RunModel(
        id=run_id,
        project_id=request.project_id,
        thread_id=request.thread_id,
        mode=request.mode,
        status=RunStatus.QUEUED.value,
        task=request.task,
        input_json=request.model_dump(mode="json"),
        checkpoint_thread_id=f"checkpoint:{run_id}",
    )
    session.add(run)
    events.append(
        session,
        run=run,
        event_type="run.created",
        status=RunStatus.QUEUED.value,
        payload={"mode": request.mode, "task": request.task},
    )
    session.commit()

    dispatcher.enqueue(run_id)
    return {"run_id": run_id, "status": RunStatus.QUEUED.value}
```

关键变化：

1. LLM 配置通过 `model_profile_id` 引用后端配置，不随每次请求传送明文 key。
2. Run 创建先落库，再入队；即使 worker 尚未启动，任务也不会丢。
3. 返回 `202 Accepted`，明确表示任务是异步执行。
4. Mock Run 不应自动 seed 到真实列表；Demo 数据放 Storybook 或 `/demo` 页面。


---

# F. 实时事件层：解决“模型输出不能实时显示”

## F.1 当前 WebSocket 的核心缺陷

当前 `/ws/runs/{run_id}` 的实现会：

1. 连接后把所有历史事件重新发送一遍；
2. 再订阅进程内 callback；
3. 用当前连接内的 `seen_event_ids` 去重。

它没有定义：

- 客户端已经消费到哪个 sequence；
- 断线后从哪里继续；
- event 是否为 token delta、完整消息、节点状态还是刷新通知；
- 多进程部署时如何跨 worker 广播；
- 慢客户端积压时如何处理；
- 相同 event 重放时如何幂等合并。

建议把 WebSocket 先收敛为 SSE。PaperPilot 当前主要是后端单向推送，SSE 更简单，也天然支持 `Last-Event-ID`。只有未来增加终端双向输入时，再单独使用 WebSocket。

## F.2 统一事件协议

```python
# backend/schemas/events_v2.py
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class EventBase(BaseModel):
    event_id: str
    run_id: str
    sequence: int
    created_at: datetime


class RunStateEvent(EventBase):
    type: Literal["run.state"]
    status: Literal[
        "queued",
        "running",
        "waiting_input",
        "waiting_approval",
        "succeeded",
        "failed",
        "cancelled",
    ]
    node_id: str | None = None
    summary: str = ""


class MessageStartedEvent(EventBase):
    type: Literal["message.started"]
    message_id: str
    role: Literal["assistant", "tool", "system"]
    agent_id: str | None = None


class MessageDeltaEvent(EventBase):
    type: Literal["message.delta"]
    message_id: str
    delta: str


class MessageCompletedEvent(EventBase):
    type: Literal["message.completed"]
    message_id: str
    finish_reason: str = "stop"


class ToolStateEvent(EventBase):
    type: Literal["tool.state"]
    tool_call_id: str
    tool_name: str
    state: Literal[
        "proposed",
        "waiting_approval",
        "running",
        "succeeded",
        "failed",
        "rejected",
    ]
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)


class ArtifactEvent(EventBase):
    type: Literal["artifact.created", "artifact.updated"]
    artifact_id: str
    kind: str
    logical_path: str
    metadata: dict = Field(default_factory=dict)


RunStreamEvent = Annotated[
    Union[
        RunStateEvent,
        MessageStartedEvent,
        MessageDeltaEvent,
        MessageCompletedEvent,
        ToolStateEvent,
        ArtifactEvent,
    ],
    Field(discriminator="type"),
]
```

注意：不要再用一个宽泛的 `payload: dict` 让前端猜结构。数据库仍可存 JSON，但 API 层必须输出判别联合类型。

## F.3 SSE 路由：支持历史补发、游标和心跳

```python
# backend/routers/event_stream.py
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.db.session import get_session_factory
from backend.repositories.events import EventRepository
from backend.services.pubsub import run_pubsub

router = APIRouter(prefix="/api/v2/runs", tags=["event-stream"])
event_repository = EventRepository()


def encode_sse(*, event_id: int, event: str, data: dict) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        f"id: {event_id}\n"
        f"event: {event}\n"
        f"data: {payload}\n\n"
    ).encode("utf-8")


@router.get("/{run_id}/events/stream")
async def stream_run_events(
    run_id: str,
    request: Request,
    after: int = 0,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    start_sequence = max(after, int(last_event_id or 0))
    session_factory = get_session_factory()

    async def iterator() -> AsyncIterator[bytes]:
        cursor = start_sequence

        # 1. 先从数据库补齐断线期间的历史事件。
        with session_factory() as session:
            backlog = event_repository.list_after(
                session,
                run_id=run_id,
                after_sequence=cursor,
            )
            for row in backlog:
                cursor = row.sequence
                yield encode_sse(
                    event_id=row.sequence,
                    event=row.event_type,
                    data={
                        "event_id": row.id,
                        "run_id": row.run_id,
                        "sequence": row.sequence,
                        "type": row.event_type,
                        **row.payload,
                        "created_at": row.created_at.isoformat(),
                    },
                )

        # 2. 再订阅通知。通知只是唤醒信号，事实仍从 DB 读取。
        subscription = run_pubsub.subscribe(run_id)
        try:
            while not await request.is_disconnected():
                try:
                    await asyncio.wait_for(subscription.get(), timeout=15)
                except TimeoutError:
                    yield b": heartbeat\n\n"
                    continue

                with session_factory() as session:
                    rows = event_repository.list_after(
                        session,
                        run_id=run_id,
                        after_sequence=cursor,
                    )
                    for row in rows:
                        cursor = row.sequence
                        yield encode_sse(
                            event_id=row.sequence,
                            event=row.event_type,
                            data={
                                "event_id": row.id,
                                "run_id": row.run_id,
                                "sequence": row.sequence,
                                "type": row.event_type,
                                **row.payload,
                                "created_at": row.created_at.isoformat(),
                            },
                        )
        finally:
            run_pubsub.unsubscribe(run_id, subscription)

    return StreamingResponse(
        iterator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

生产环境的 `run_pubsub` 可以用 Redis Pub/Sub；单进程开发环境可以用 `asyncio.Queue`。无论哪一种，通知丢失都不影响正确性，因为客户端最终从数据库按 sequence 补齐。

## F.4 LLM token 流必须进入同一个 Event Store

当前前端看到的大多是节点级 `node_started`，不是模型 token。应在 Provider 层统一流式接口。

```python
# backend/llm/base.py
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class TextDelta:
    text: str


@dataclass(slots=True)
class UsageDelta:
    input_tokens: int = 0
    output_tokens: int = 0


LLMDelta = TextDelta | UsageDelta


class StreamingLLM(Protocol):
    async def stream_text(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0,
    ) -> AsyncIterator[LLMDelta]: ...
```

```python
# backend/services/agent_message_writer.py
from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from backend.db.models import RunModel
from backend.llm.base import StreamingLLM, TextDelta, UsageDelta
from backend.repositories.events import EventRepository


class AgentMessageWriter:
    def __init__(self, llm: StreamingLLM, events: EventRepository) -> None:
        self.llm = llm
        self.events = events

    async def generate(
        self,
        session: Session,
        *,
        run: RunModel,
        agent_id: str,
        node_id: str,
        messages: list[dict[str, str]],
        model: str,
    ) -> str:
        message_id = f"msg_{uuid4().hex}"
        self.events.append(
            session,
            run=run,
            event_type="message.started",
            node_id=node_id,
            agent_id=agent_id,
            message_id=message_id,
            payload={
                "message_id": message_id,
                "role": "assistant",
                "agent_id": agent_id,
            },
        )
        session.commit()

        chunks: list[str] = []
        usage = {"input_tokens": 0, "output_tokens": 0}

        async for delta in self.llm.stream_text(
            messages=messages,
            model=model,
        ):
            if isinstance(delta, TextDelta):
                chunks.append(delta.text)
                self.events.append(
                    session,
                    run=run,
                    event_type="message.delta",
                    node_id=node_id,
                    agent_id=agent_id,
                    message_id=message_id,
                    payload={"message_id": message_id, "delta": delta.text},
                )
                session.commit()
            elif isinstance(delta, UsageDelta):
                usage["input_tokens"] += delta.input_tokens
                usage["output_tokens"] += delta.output_tokens

        full_text = "".join(chunks)
        self.events.append(
            session,
            run=run,
            event_type="message.completed",
            node_id=node_id,
            agent_id=agent_id,
            message_id=message_id,
            payload={
                "message_id": message_id,
                "finish_reason": "stop",
                "usage": usage,
                "content": full_text,
            },
        )
        session.commit()
        return full_text
```

为减少数据库写放大，可以把 20–50 ms 内的 delta 合并后写入，但不能只在结尾写完整文本，否则前端仍然不是流式。

---

# G. LangGraph：让计划编辑和审批真正控制执行

## G.1 当前 `interrupt_after` 为什么不够

当前 `graph_hitl_runner.py` 通过：

```python
interrupt_after=("research_understanding", "reproduction_planner")
```

实现暂停，再尝试用 `Command(resume=...)`、`None`、`{}` 三种输入恢复。问题是：

- Pause 没有携带严格结构化的审核数据；
- Resume 没有明确的 action schema；
- 用户编辑后的计划没有更新到 graph state；
- command risk 三个分支最终都会继续执行生成，不是真正 gate；
- Checkpointer 是 `InMemorySaver`，重启即丢失。

## G.2 持久 Checkpointer

开发环境可先使用 SQLite，生产使用 PostgresSaver。

```python
# pipeline/graph_checkpointer.py
from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.sqlite import SqliteSaver

from config import WORKSPACE_DIR


@lru_cache(maxsize=1)
def get_graph_checkpointer() -> SqliteSaver:
    checkpoint_path = WORKSPACE_DIR / "state" / "langgraph.sqlite"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    connection_string = str(checkpoint_path)
    saver = SqliteSaver.from_conn_string(connection_string)
    saver.setup()
    return saver
```

生产实现：

```python
# pipeline/graph_checkpointer_postgres.py
from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver

from config import settings


@lru_cache(maxsize=1)
def get_graph_checkpointer() -> PostgresSaver:
    saver = PostgresSaver.from_conn_string(settings.database_url)
    saver.setup()
    return saver
```

## G.3 Typed Plan 与 Resume Contract

```python
# schemas/plan_schema.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    id: str
    title: str
    description: str
    agent: str
    enabled: bool = True
    depends_on: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    risk: Literal["low", "medium", "high"] = "low"


class EditablePlan(BaseModel):
    revision: int = 1
    objective: str
    steps: list[PlanStep]


class PlanReviewDecision(BaseModel):
    action: Literal["approve", "edit", "reject"]
    plan: EditablePlan | None = None
    feedback: str = ""


class ToolReviewDecision(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_input: dict | None = None
    feedback: str = ""
```

## G.4 在节点内部调用 `interrupt()`，而不是只用 `interrupt_after`

```python
# graphs/nodes/plan_review.py
from __future__ import annotations

from langgraph.types import interrupt

from schemas.plan_schema import EditablePlan, PlanReviewDecision


def review_plan_node(state: dict) -> dict:
    plan = EditablePlan.model_validate(state["editable_plan"])

    raw_decision = interrupt(
        {
            "kind": "plan_review",
            "title": "Review execution plan",
            "plan": plan.model_dump(mode="json"),
            "allowed_actions": ["approve", "edit", "reject"],
        }
    )
    decision = PlanReviewDecision.model_validate(raw_decision)

    if decision.action == "reject":
        return {
            "plan_review_status": "rejected",
            "errors": [decision.feedback or "User rejected the plan."],
        }

    effective_plan = decision.plan if decision.action == "edit" else plan
    if effective_plan is None:
        raise ValueError("Edited plan is required when action=edit")

    return {
        "editable_plan": effective_plan.model_dump(mode="json"),
        "plan_review_status": "approved",
        "user_plan_feedback": decision.feedback,
    }
```

```python
# graphs/nodes/tool_review.py
from __future__ import annotations

from langgraph.types import interrupt

from schemas.plan_schema import ToolReviewDecision


def tool_review_node(state: dict) -> dict:
    tool_request = dict(state["pending_tool_request"])
    raw = interrupt(
        {
            "kind": "tool_review",
            "tool_request": tool_request,
            "risk": tool_request.get("risk", "medium"),
            "allowed_actions": ["approve", "edit", "reject"],
        }
    )
    decision = ToolReviewDecision.model_validate(raw)

    if decision.action == "reject":
        return {
            "tool_review_status": "rejected",
            "tool_result": {
                "executed": False,
                "reason": decision.feedback or "Rejected by user",
            },
        }

    if decision.action == "edit":
        tool_request["input"] = decision.edited_input or {}

    return {
        "tool_review_status": "approved",
        "approved_tool_request": tool_request,
    }
```

## G.5 Reproduce Graph 的正确条件路由

当前 safe/review/blocked 三个 summary 都连接到 `reproduction_implementation`。建议改为：

```python
# graphs/reproduce_graph_v2.py（核心片段）
from langgraph.graph import END, START, StateGraph


def route_tool_request(state: dict) -> str:
    risk = state["pending_tool_request"]["risk"]
    if risk == "blocked":
        return "blocked"
    if risk in {"medium", "high"}:
        return "review"
    return "execute"


def route_after_review(state: dict) -> str:
    return (
        "execute"
        if state.get("tool_review_status") == "approved"
        else "skip"
    )


builder = StateGraph(ReproduceStateV2)
builder.add_node("parse_paper", parse_paper_node)
builder.add_node("index_repository", index_repository_node)
builder.add_node("build_evidence", build_evidence_node)
builder.add_node("draft_plan", draft_plan_node)
builder.add_node("review_plan", review_plan_node)
builder.add_node("materialize_step", materialize_next_step_node)
builder.add_node("review_tool", tool_review_node)
builder.add_node("execute_tool", execute_tool_node)
builder.add_node("record_blocked", record_blocked_node)
builder.add_node("record_skipped", record_skipped_node)
builder.add_node("verify", verify_node)
builder.add_node("repair", repair_node)
builder.add_node("finish", finish_node)

builder.add_edge(START, "parse_paper")
builder.add_edge("parse_paper", "index_repository")
builder.add_edge("index_repository", "build_evidence")
builder.add_edge("build_evidence", "draft_plan")
builder.add_edge("draft_plan", "review_plan")
builder.add_edge("review_plan", "materialize_step")

builder.add_conditional_edges(
    "materialize_step",
    route_tool_request,
    {
        "execute": "execute_tool",
        "review": "review_tool",
        "blocked": "record_blocked",
    },
)
builder.add_conditional_edges(
    "review_tool",
    route_after_review,
    {"execute": "execute_tool", "skip": "record_skipped"},
)

for node in ("execute_tool", "record_blocked", "record_skipped"):
    builder.add_edge(node, "verify")

builder.add_conditional_edges(
    "verify",
    lambda state: "finish" if state["verification"]["passed"] else "repair",
    {"finish": "finish", "repair": "repair"},
)
builder.add_edge("repair", "verify")
builder.add_edge("finish", END)

graph = builder.compile(checkpointer=get_graph_checkpointer())
```

## G.6 API 恢复 Graph

```python
# backend/routers/run_resume.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import RunStatus
from backend.db.session import get_session
from backend.services.run_application_service import RunApplicationService
from backend.workers.dispatcher import dispatcher

router = APIRouter(prefix="/api/v2/runs", tags=["run-resume"])


class ResumeRequest(BaseModel):
    interrupt_id: str
    value: dict


@router.post("/{run_id}/resume", status_code=202)
def resume_run(
    run_id: str,
    request: ResumeRequest,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    # 先持久化用户决定，再由 worker 恢复。不要在 HTTP handler 内直接长时间 graph.invoke。
    dispatcher.enqueue_resume(
        run_id=run_id,
        command=Command(resume=request.value),
        interrupt_id=request.interrupt_id,
    )
    return {"run_id": run_id, "status": RunStatus.QUEUED.value}
```

## G.7 Worker 恢复与取消

```python
# backend/workers/run_worker.py
from __future__ import annotations

from dataclasses import dataclass

from langgraph.types import Command
from sqlalchemy.orm import Session

from backend.db.models import RunModel, RunStatus
from backend.repositories.events import EventRepository
from graphs.registry import graph_for_mode


@dataclass(slots=True)
class RunJob:
    run_id: str
    resume_command: Command | None = None


class RunWorker:
    def __init__(self, session_factory, events: EventRepository) -> None:
        self.session_factory = session_factory
        self.events = events

    def execute(self, job: RunJob) -> None:
        with self.session_factory() as session:
            run = session.get(RunModel, job.run_id)
            if run is None:
                return
            if run.cancel_requested:
                self._mark_cancelled(session, run)
                return

            run.status = RunStatus.RUNNING.value
            self.events.append(
                session,
                run=run,
                event_type="run.state",
                status=RunStatus.RUNNING.value,
                payload={"status": RunStatus.RUNNING.value},
            )
            session.commit()

            graph = graph_for_mode(run.mode)
            config = {
                "configurable": {
                    "thread_id": run.checkpoint_thread_id,
                    "run_id": run.id,
                }
            }

        try:
            graph_input = job.resume_command or run.input_json
            graph.invoke(graph_input, config=config)
            snapshot = graph.get_state(config)

            with self.session_factory() as session:
                run = session.get(RunModel, job.run_id)
                if run is None:
                    return
                if snapshot.next:
                    run.status = RunStatus.WAITING_APPROVAL.value
                    event_type = "run.interrupted"
                    payload = {
                        "status": run.status,
                        "interrupts": [
                            item.value
                            for task in snapshot.tasks
                            for item in task.interrupts
                        ],
                    }
                else:
                    run.status = RunStatus.SUCCEEDED.value
                    run.result_json = dict(snapshot.values)
                    event_type = "run.completed"
                    payload = {"status": run.status}

                self.events.append(
                    session,
                    run=run,
                    event_type=event_type,
                    status=run.status,
                    payload=payload,
                )
                session.commit()
        except Exception as exc:
            with self.session_factory() as session:
                run = session.get(RunModel, job.run_id)
                if run is None:
                    return
                run.status = RunStatus.FAILED.value
                run.error_json = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
                self.events.append(
                    session,
                    run=run,
                    event_type="run.failed",
                    status=run.status,
                    payload={"status": run.status, "error": run.error_json},
                )
                session.commit()

    def _mark_cancelled(self, session: Session, run: RunModel) -> None:
        run.status = RunStatus.CANCELLED.value
        self.events.append(
            session,
            run=run,
            event_type="run.cancelled",
            status=run.status,
            payload={"status": run.status},
        )
        session.commit()
```

取消不能只改 UI。每一个长步骤、每次 LLM 调用前后和每个工具调用之间，都应读取 `cancel_requested`，必要时抛出专用 `RunCancelled`。


---

# H. 真正的 Sandbox、构建、测试与预览

## H.1 当前 `run_command_sandbox()` 不是隔离边界

当前实现：

```python
sandbox_dir = tempfile.mkdtemp(...)
_copytree(resolved_cwd, sandbox_dir)
subprocess.run(..., cwd=sandbox_dir)
```

它只隔离了“工作目录”，没有隔离：

- 宿主机用户权限；
- 文件系统其他路径；
- 网络；
- 进程、CPU、内存、PID；
- pip/npm 安装位置和缓存；
- fork bomb 或大量子进程；
- 对 `/proc`、环境变量和宿主服务的访问。

更严重的是 `run_sandbox_verification()` 会执行 `pip install -r requirements.txt`，依赖安装仍发生在宿主 Python 环境。

## H.2 Docker Runner：命令必须使用 argv，不接受任意 shell 字符串

```python
# backend/runtime/docker_runner.py
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence
from uuid import uuid4

import docker
from docker.errors import ContainerError, ImageNotFound


@dataclass(slots=True)
class ContainerLimits:
    memory: str = "2g"
    nano_cpus: int = 2_000_000_000  # 2 CPU
    pids_limit: int = 256
    timeout_seconds: int = 300
    network_enabled: bool = False


@dataclass(slots=True)
class ContainerResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    container_id: str = ""
    artifacts: list[str] = field(default_factory=list)


class DockerRunner:
    def __init__(self, workspace_root: Path) -> None:
        self.client = docker.from_env()
        self.workspace_root = workspace_root.resolve()

    def run(
        self,
        *,
        source_dir: Path,
        image: str,
        argv: Sequence[str],
        limits: ContainerLimits,
        environment: dict[str, str] | None = None,
    ) -> ContainerResult:
        source_dir = source_dir.resolve()
        if not source_dir.is_relative_to(self.workspace_root):
            raise ValueError("source_dir must be under workspace root")
        if not argv or any("\x00" in part for part in argv):
            raise ValueError("Invalid argv")

        container_name = f"paperpilot-job-{uuid4().hex[:12]}"
        network_mode = "none" if not limits.network_enabled else "bridge"

        container = self.client.containers.create(
            image=image,
            name=container_name,
            command=list(argv),
            working_dir="/workspace",
            environment={
                "HOME": "/tmp/home",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                **(environment or {}),
            },
            volumes={
                str(source_dir): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
            network_mode=network_mode,
            mem_limit=limits.memory,
            nano_cpus=limits.nano_cpus,
            pids_limit=limits.pids_limit,
            read_only=True,
            tmpfs={
                "/tmp": "rw,noexec,nosuid,size=512m",
                "/tmp/home": "rw,noexec,nosuid,size=64m",
            },
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            user="1000:1000",
            detach=True,
            stdout=True,
            stderr=True,
        )

        try:
            container.start()
            wait_result = container.wait(timeout=limits.timeout_seconds)
            stdout = container.logs(stdout=True, stderr=False).decode(
                "utf-8", errors="replace"
            )
            stderr = container.logs(stdout=False, stderr=True).decode(
                "utf-8", errors="replace"
            )
            return ContainerResult(
                exit_code=int(wait_result.get("StatusCode", 1)),
                stdout=stdout[-100_000:],
                stderr=stderr[-100_000:],
                container_id=container.id,
            )
        except Exception as exc:
            try:
                container.kill()
            except Exception:
                pass
            return ContainerResult(
                exit_code=None,
                stdout="",
                stderr=str(exc),
                timed_out=True,
                container_id=container.id,
            )
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass
```

### 额外要求

- 不把 Docker socket 挂进执行容器；
- 容器中不传入 LLM API Key；
- 默认 `network_mode=none`；
- 安装依赖阶段若必须联网，使用单独的受控 builder，并配置域名白名单、缓存和超时；
- 运行镜像固定 digest，不使用漂移的 `latest`；
- 挂载目录只允许当前 run workspace；
- 日志输出限制大小，防止内存耗尽；
- 每个 run 建立独立 UID / workspace。

## H.3 两阶段构建，避免安装阶段无限联网

```python
# backend/runtime/build_pipeline.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.runtime.docker_runner import ContainerLimits, DockerRunner


@dataclass(slots=True)
class BuildReport:
    passed: bool
    install_log: str
    build_log: str
    test_log: str
    failure_stage: str | None = None


class ProjectBuildPipeline:
    def __init__(self, runner: DockerRunner) -> None:
        self.runner = runner

    def verify_nextjs(self, project_dir: Path) -> BuildReport:
        install = self.runner.run(
            source_dir=project_dir,
            image="node:20.16.0-alpine@sha256:<PINNED_DIGEST>",
            argv=["npm", "ci", "--ignore-scripts", "--no-audit"],
            limits=ContainerLimits(
                memory="3g",
                timeout_seconds=300,
                network_enabled=True,
            ),
            environment={"NPM_CONFIG_CACHE": "/tmp/npm-cache"},
        )
        if install.exit_code != 0:
            return BuildReport(
                passed=False,
                install_log=install.stdout + install.stderr,
                build_log="",
                test_log="",
                failure_stage="install",
            )

        build = self.runner.run(
            source_dir=project_dir,
            image="node:20.16.0-alpine@sha256:<PINNED_DIGEST>",
            argv=["npm", "run", "build"],
            limits=ContainerLimits(memory="3g", timeout_seconds=300),
        )
        if build.exit_code != 0:
            return BuildReport(
                passed=False,
                install_log=install.stdout,
                build_log=build.stdout + build.stderr,
                test_log="",
                failure_stage="build",
            )

        tests = self.runner.run(
            source_dir=project_dir,
            image="node:20.16.0-alpine@sha256:<PINNED_DIGEST>",
            argv=["npm", "test", "--", "--run"],
            limits=ContainerLimits(memory="3g", timeout_seconds=180),
        )
        return BuildReport(
            passed=tests.exit_code == 0,
            install_log=install.stdout,
            build_log=build.stdout,
            test_log=tests.stdout + tests.stderr,
            failure_stage=None if tests.exit_code == 0 else "test",
        )
```

实际生产中，`npm ci` 生成的 `node_modules` 需要保存在同一个受控 volume 或 builder image 中；上面的代码表达的是隔离结构。不要让每个阶段重新在空容器里安装又丢失依赖。

## H.4 Productize 不应继续生成 static mock-first bundle

当前 `product_scaffold.py` 明确：

- 调用 `build_static_bundle_sources()`；
- README 写着 deterministic mock adapter；
- frontend 通过 `python -m http.server` 启动；
- `mock_first: True` 固定写入 manifest；
- “Real Model Integration” 留给用户手工改 `adapter.js`。

这与“把论文 Idea 转成真实可用产品”的目标不一致。建议把生成单元改成一个严格合同：

```python
# schemas/generated_app.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GeneratedFile(BaseModel):
    path: str
    content: str
    purpose: str


class AppContract(BaseModel):
    runtime: Literal["nextjs"] = "nextjs"
    package_manager: Literal["npm"] = "npm"
    required_scripts: dict[str, str] = Field(
        default_factory=lambda: {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "test": "vitest run",
        }
    )
    required_routes: list[str]
    required_components: list[str]
    required_api_routes: list[str]
    acceptance_tests: list[str]
    real_adapter_required: bool = True
    mock_fallback_allowed: bool = True


class GeneratedAppBundle(BaseModel):
    contract: AppContract
    files: list[GeneratedFile]
    integration_notes: list[str] = Field(default_factory=list)
```

生成器写文件前必须检查路径与数量：

```python
# productize/next_app_writer.py
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath

from schemas.generated_app import GeneratedAppBundle


MAX_FILES = 160
MAX_TOTAL_BYTES = 4 * 1024 * 1024
ALLOWED_ROOTS = {
    "app",
    "components",
    "lib",
    "public",
    "tests",
    "styles",
}
ALLOWED_ROOT_FILES = {
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "next.config.mjs",
    "postcss.config.mjs",
    "tailwind.config.ts",
    "README.md",
    ".gitignore",
}


def validate_generated_path(raw: str) -> PurePosixPath:
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Unsafe generated path: {raw}")
    if len(path.parts) == 1:
        if path.name not in ALLOWED_ROOT_FILES:
            raise ValueError(f"Unexpected root file: {raw}")
    elif path.parts[0] not in ALLOWED_ROOTS:
        raise ValueError(f"Unexpected root directory: {raw}")
    return path


def write_bundle(bundle: GeneratedAppBundle, destination: Path) -> dict:
    if len(bundle.files) > MAX_FILES:
        raise ValueError("Too many generated files")

    total_bytes = sum(len(item.content.encode("utf-8")) for item in bundle.files)
    if total_bytes > MAX_TOTAL_BYTES:
        raise ValueError("Generated app exceeds size limit")

    destination.mkdir(parents=True, exist_ok=False)
    manifest: list[dict] = []
    seen: set[str] = set()

    for item in bundle.files:
        relative = validate_generated_path(item.path)
        normalized = relative.as_posix()
        if normalized in seen:
            raise ValueError(f"Duplicate file: {normalized}")
        seen.add(normalized)

        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item.content, encoding="utf-8")
        manifest.append(
            {
                "path": normalized,
                "sha256": hashlib.sha256(
                    item.content.encode("utf-8")
                ).hexdigest(),
                "purpose": item.purpose,
            }
        )

    return {"files": manifest, "contract": bundle.contract.model_dump()}
```

## H.5 Build-Test-Repair 不能靠关键词路由

当前路由会从 evaluator 文本中搜索 `ui/adapter/mock/syntax/readme/prototype`。建议 verifier 输出 typed issue：

```python
# schemas/verification.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


IssueCategory = Literal[
    "dependency",
    "typescript",
    "build",
    "unit_test",
    "browser_runtime",
    "api_contract",
    "adapter_integration",
    "security",
    "ux_acceptance",
]


class VerificationIssue(BaseModel):
    id: str
    category: IssueCategory
    severity: Literal["error", "warning"]
    path: str | None = None
    line: int | None = None
    message: str
    evidence: str = ""
    suggested_owner: Literal[
        "generator",
        "adapter_agent",
        "ui_agent",
        "dependency_agent",
    ]


class VerificationReport(BaseModel):
    passed: bool
    stage: Literal["install", "build", "test", "browser", "contract"]
    issues: list[VerificationIssue] = Field(default_factory=list)
    raw_log_artifact_id: str | None = None
```

路由只看结构化字段：

```python
# runtime/routing_v2.py
from schemas.verification import VerificationReport


def route_after_verification(state: dict) -> str:
    report = VerificationReport.model_validate(state["verification_report"])
    attempts = int(state.get("repair_attempts", 0))
    max_attempts = int(state.get("max_repair_attempts", 3))

    if report.passed:
        return "browser_test"
    if attempts >= max_attempts:
        return "fail_with_report"

    owners = {issue.suggested_owner for issue in report.issues}
    if "dependency_agent" in owners:
        return "repair_dependencies"
    if "adapter_agent" in owners:
        return "repair_adapter"
    if "ui_agent" in owners:
        return "repair_ui"
    return "repair_code"
```

## H.6 Playwright 浏览器验收

静态字符串 marker 不能证明页面可用。生成产品至少需要：

```ts
// generated-app/tests/e2e/product.spec.ts
import { expect, test } from "@playwright/test";

test("primary workflow can complete", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /paper|research|demo/i }),
  ).toBeVisible();

  const upload = page.getByLabel(/upload|input file/i);
  if (await upload.isVisible()) {
    await upload.setInputFiles("tests/fixtures/sample.png");
  }

  const primaryAction = page.getByRole("button", {
    name: /run|analyze|generate|predict/i,
  });
  await expect(primaryAction).toBeEnabled();
  await primaryAction.click();

  await expect(
    page.getByTestId("result-panel"),
  ).toBeVisible({ timeout: 30_000 });

  await expect(page.locator("body")).not.toContainText(
    /uncaught|internal server error|cannot read properties/i,
  );
});
```

```ts
// generated-app/playwright.config.ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  retries: 1,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "npm run dev -- --hostname 0.0.0.0",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
```

## H.7 Preview Manager

```python
# backend/runtime/preview_manager.py
from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import docker


@dataclass(slots=True)
class PreviewInstance:
    id: str
    run_id: str
    container_id: str
    host_port: int
    status: str


def reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class PreviewManager:
    def __init__(self) -> None:
        self.client = docker.from_env()
        self.instances: dict[str, PreviewInstance] = {}

    def start(self, *, run_id: str, project_dir: Path) -> PreviewInstance:
        preview_id = f"preview_{uuid4().hex[:12]}"
        port = reserve_port()
        container = self.client.containers.run(
            image="paperpilot-next-preview:20",
            command=["npm", "run", "dev", "--", "--hostname", "0.0.0.0"],
            working_dir="/workspace",
            volumes={
                str(project_dir.resolve()): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
            ports={"3000/tcp": ("127.0.0.1", port)},
            network_mode="bridge",
            mem_limit="2g",
            nano_cpus=2_000_000_000,
            pids_limit=256,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            detach=True,
            remove=False,
        )
        instance = PreviewInstance(
            id=preview_id,
            run_id=run_id,
            container_id=container.id,
            host_port=port,
            status="starting",
        )
        self.instances[preview_id] = instance
        return instance

    def stop(self, preview_id: str) -> None:
        instance = self.instances.pop(preview_id, None)
        if instance is None:
            return
        container = self.client.containers.get(instance.container_id)
        container.remove(force=True)
```

后端代理 `/api/previews/{preview_id}/{path:path}` 时必须：

- 只代理 registry 中存在且属于当前用户/project 的 preview；
- 删除上游 `Set-Cookie` 等敏感 header；
- 配置 CSP 和 iframe sandbox；
- 支持 WebSocket upgrade，保证 Next.js HMR；
- Preview 到期自动停止；
- 并发数和磁盘占用设配额。


---

# I. 前端重构：从 `WorkspaceShell` 拆成 Chat-first Workbench

## I.1 现状为什么容易出现状态竞争

当前 `WorkspaceShell` 同时持有：

- Run 与 active run 恢复；
- Timeline events；
- Graph；
- Actions / Commands；
- Result；
- 上传表单；
- LLM 配置和 API Key；
- Plan 选择和编辑；
- Approval Drawer；
- 文件编辑器；
- Preview / Inspector；
- Bottom Dock；
- 各类 mock fallback。

收到 WebSocket 事件后，又会并发获取多个资源。即使每个请求本身正确，也可能发生：

```text
事件 sequence=18 到达
  ├── GET run 返回 version 18，较慢
  ├── GET result 返回旧 version 17，较快
  └── GET graph 返回由关键词推断出的 version 18

事件 sequence=19 到达
  ├── 新一轮五个请求
  └── 旧请求稍后返回，覆盖新 state
```

所以不能只加 `AbortController` 或 debounce。需要把“服务端事实状态”和“本地 UI 状态”分开。

## I.2 推荐目录

```text
frontend/
├── app/
│   └── projects/[projectId]/threads/[threadId]/page.tsx
├── features/
│   ├── runs/
│   │   ├── api.ts
│   │   ├── event-reducer.ts
│   │   ├── run-store.ts
│   │   ├── use-run-stream.ts
│   │   └── run-status-pill.tsx
│   ├── chat/
│   │   ├── conversation.tsx
│   │   ├── message.tsx
│   │   ├── message-parts.tsx
│   │   └── composer.tsx
│   ├── approvals/
│   │   ├── approval-card.tsx
│   │   └── plan-review-card.tsx
│   ├── artifacts/
│   │   ├── artifact-panel.tsx
│   │   └── code-editor.tsx
│   └── preview/
│       └── preview-panel.tsx
├── stores/
│   └── ui-store.ts
└── lib/
    ├── http.ts
    └── errors.ts
```

## I.3 服务端事实状态 Store

这个 store 只通过快照 hydrate 或事件 reduce 更新。组件不能随意 `setRunStatus()`。

```ts
// frontend/features/runs/run-store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { RunEvent, RunSnapshot, RunViewState } from "./types";
import { applyRunEvent } from "./event-reducer";

type RunStore = {
  runs: Record<string, RunViewState>;
  hydrate: (snapshot: RunSnapshot) => void;
  applyEvent: (event: RunEvent) => void;
  reset: (runId: string) => void;
};

function snapshotToViewState(snapshot: RunSnapshot): RunViewState {
  return {
    runId: snapshot.runId,
    status: snapshot.status,
    currentNode: snapshot.currentNode,
    lastSequence: snapshot.lastSequence,
    messages: snapshot.messages,
    messageOrder: snapshot.messageOrder,
    tools: snapshot.tools,
    toolOrder: snapshot.toolOrder,
    artifacts: snapshot.artifacts,
    artifactOrder: snapshot.artifactOrder,
    interrupts: snapshot.interrupts,
    summary: snapshot.summary,
    error: snapshot.error,
  };
}

export const useRunStore = create<RunStore>()(
  devtools(
    (set) => ({
      runs: {},

      hydrate: (snapshot) =>
        set(
          (state) => {
            const current = state.runs[snapshot.runId];
            // 不允许旧快照覆盖已经消费到更高 sequence 的流式状态。
            if (current && current.lastSequence > snapshot.lastSequence) {
              return state;
            }
            return {
              runs: {
                ...state.runs,
                [snapshot.runId]: snapshotToViewState(snapshot),
              },
            };
          },
          false,
          "runs/hydrate",
        ),

      applyEvent: (event) =>
        set(
          (state) => {
            const current = state.runs[event.runId];
            if (!current) {
              return state;
            }
            if (event.sequence <= current.lastSequence) {
              return state;
            }
            return {
              runs: {
                ...state.runs,
                [event.runId]: applyRunEvent(current, event),
              },
            };
          },
          false,
          `runs/event/${event.type}`,
        ),

      reset: (runId) =>
        set((state) => {
          const runs = { ...state.runs };
          delete runs[runId];
          return { runs };
        }),
    }),
    { name: "paperpilot-run-store" },
  ),
);
```

## I.4 幂等 Event Reducer

```ts
// frontend/features/runs/event-reducer.ts
import type {
  AssistantMessage,
  RunEvent,
  RunViewState,
  ToolCallView,
} from "./types";

export function applyRunEvent(
  state: RunViewState,
  event: RunEvent,
): RunViewState {
  if (event.sequence <= state.lastSequence) return state;

  const next: RunViewState = {
    ...state,
    lastSequence: event.sequence,
  };

  switch (event.type) {
    case "run.state":
      return {
        ...next,
        status: event.status,
        currentNode: event.nodeId ?? state.currentNode,
        summary: event.summary ?? state.summary,
      };

    case "message.started": {
      if (state.messages[event.messageId]) return next;
      const message: AssistantMessage = {
        id: event.messageId,
        role: event.role,
        agentId: event.agentId,
        content: "",
        status: "streaming",
      };
      return {
        ...next,
        messages: {
          ...state.messages,
          [message.id]: message,
        },
        messageOrder: [...state.messageOrder, message.id],
      };
    }

    case "message.delta": {
      const current = state.messages[event.messageId];
      if (!current) return next;
      return {
        ...next,
        messages: {
          ...state.messages,
          [event.messageId]: {
            ...current,
            content: current.content + event.delta,
          },
        },
      };
    }

    case "message.completed": {
      const current = state.messages[event.messageId];
      if (!current) return next;
      return {
        ...next,
        messages: {
          ...state.messages,
          [event.messageId]: {
            ...current,
            status: "completed",
            finishReason: event.finishReason,
          },
        },
      };
    }

    case "tool.state": {
      const existing = state.tools[event.toolCallId];
      const tool: ToolCallView = {
        id: event.toolCallId,
        name: event.toolName,
        state: event.state,
        input: event.input ?? existing?.input ?? {},
        output: event.output ?? existing?.output ?? {},
      };
      return {
        ...next,
        tools: { ...state.tools, [tool.id]: tool },
        toolOrder: existing
          ? state.toolOrder
          : [...state.toolOrder, tool.id],
      };
    }

    case "artifact.created":
    case "artifact.updated": {
      const exists = Boolean(state.artifacts[event.artifactId]);
      return {
        ...next,
        artifacts: {
          ...state.artifacts,
          [event.artifactId]: {
            id: event.artifactId,
            kind: event.kind,
            logicalPath: event.logicalPath,
            metadata: event.metadata,
          },
        },
        artifactOrder: exists
          ? state.artifactOrder
          : [...state.artifactOrder, event.artifactId],
      };
    }

    case "run.interrupted":
      return {
        ...next,
        status: "waiting_approval",
        interrupts: event.interrupts,
      };

    case "run.failed":
      return {
        ...next,
        status: "failed",
        error: event.error,
      };

    default: {
      const exhaustiveCheck: never = event;
      return exhaustiveCheck;
    }
  }
}
```

## I.5 SSE Hook：只消费增量，不对每个事件执行五次 GET

```ts
// frontend/features/runs/use-run-stream.ts
"use client";

import { useEffect, useRef, useState } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { z } from "zod";

import { API_BASE } from "@/lib/http";
import { runEventSchema } from "./event-schemas";
import { useRunStore } from "./run-store";

class RetriableStreamError extends Error {}
class FatalStreamError extends Error {}

export function useRunStream(runId: string | null) {
  const applyEvent = useRunStore((state) => state.applyEvent);
  const lastSequence = useRunStore(
    (state) => (runId ? state.runs[runId]?.lastSequence ?? 0 : 0),
  );
  const [connectionState, setConnectionState] = useState<
    "idle" | "connecting" | "open" | "reconnecting" | "closed"
  >("idle");
  const sequenceRef = useRef(lastSequence);

  useEffect(() => {
    sequenceRef.current = lastSequence;
  }, [lastSequence]);

  useEffect(() => {
    if (!runId) return;

    const controller = new AbortController();
    setConnectionState("connecting");

    void fetchEventSource(
      `${API_BASE}/api/v2/runs/${runId}/events/stream?after=${sequenceRef.current}`,
      {
        signal: controller.signal,
        headers: {
          Accept: "text/event-stream",
          "Last-Event-ID": String(sequenceRef.current),
        },
        openWhenHidden: true,

        async onopen(response) {
          if (response.ok) {
            setConnectionState("open");
            return;
          }
          if (response.status >= 400 && response.status < 500) {
            throw new FatalStreamError(`Stream rejected: ${response.status}`);
          }
          throw new RetriableStreamError(
            `Stream unavailable: ${response.status}`,
          );
        },

        onmessage(message) {
          if (!message.data) return;
          const parsedJson: unknown = JSON.parse(message.data);
          const event = runEventSchema.parse(parsedJson);
          if (event.sequence <= sequenceRef.current) return;
          sequenceRef.current = event.sequence;
          applyEvent(event);
        },

        onclose() {
          if (!controller.signal.aborted) {
            throw new RetriableStreamError("Stream closed unexpectedly");
          }
        },

        onerror(error) {
          if (error instanceof FatalStreamError) {
            setConnectionState("closed");
            throw error;
          }
          setConnectionState("reconnecting");
          // 返回 undefined 让库按退避策略重试。
        },
      },
    );

    return () => {
      controller.abort();
      setConnectionState("closed");
    };
  }, [runId, applyEvent]);

  return connectionState;
}
```

## I.6 首次快照与断线校准使用 TanStack Query

```ts
// frontend/features/runs/use-run.ts
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/http";
import { useRunStore } from "./run-store";
import type { RunSnapshot } from "./types";

export function useRun(runId: string | null) {
  const hydrate = useRunStore((state) => state.hydrate);

  return useQuery({
    queryKey: ["run", runId],
    enabled: Boolean(runId),
    queryFn: async () => {
      const snapshot = await api.get<RunSnapshot>(
        `/api/v2/runs/${runId}/snapshot`,
      );
      hydrate(snapshot);
      return snapshot;
    },
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}
```

不要再为 `run`、`graph`、`actions`、`commands`、`result` 分别发请求。`snapshot` 应是一个一致版本的聚合读模型：

```json
{
  "runId": "run_xxx",
  "status": "running",
  "lastSequence": 42,
  "messages": {},
  "tools": {},
  "artifacts": {},
  "interrupts": [],
  "graph": {
    "nodes": [],
    "edges": []
  }
}
```

## I.7 UI Store 只保存本地偏好

```ts
// frontend/stores/ui-store.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

type InspectorTab = "preview" | "artifacts" | "code" | "graph";

type UiState = {
  sidebarOpen: boolean;
  inspectorOpen: boolean;
  inspectorWidth: number;
  inspectorTab: InspectorTab;
  selectedArtifactId: string | null;
  commandPaletteOpen: boolean;
  setSidebarOpen: (value: boolean) => void;
  setInspectorOpen: (value: boolean) => void;
  setInspectorWidth: (value: number) => void;
  setInspectorTab: (value: InspectorTab) => void;
  setSelectedArtifactId: (value: string | null) => void;
  setCommandPaletteOpen: (value: boolean) => void;
};

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      inspectorOpen: true,
      inspectorWidth: 520,
      inspectorTab: "preview",
      selectedArtifactId: null,
      commandPaletteOpen: false,
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      setInspectorOpen: (inspectorOpen) => set({ inspectorOpen }),
      setInspectorWidth: (inspectorWidth) => set({ inspectorWidth }),
      setInspectorTab: (inspectorTab) => set({ inspectorTab }),
      setSelectedArtifactId: (selectedArtifactId) =>
        set({ selectedArtifactId }),
      setCommandPaletteOpen: (commandPaletteOpen) =>
        set({ commandPaletteOpen }),
    }),
    {
      name: "paperpilot-ui",
      partialize: (state) => ({
        sidebarOpen: state.sidebarOpen,
        inspectorOpen: state.inspectorOpen,
        inspectorWidth: state.inspectorWidth,
        inspectorTab: state.inspectorTab,
      }),
    },
  ),
);
```

绝对不要把 token 流、Run status 或审批状态持久化到 localStorage。那些都应从后端恢复。

## I.8 顶层 Workspace 变薄

```tsx
// frontend/features/workbench/workbench.tsx
"use client";

import { Conversation } from "@/features/chat/conversation";
import { Composer } from "@/features/chat/composer";
import { InspectorPanel } from "@/features/inspector/inspector-panel";
import { ProjectSidebar } from "@/features/projects/project-sidebar";
import { useRun } from "@/features/runs/use-run";
import { useRunStream } from "@/features/runs/use-run-stream";
import { useUiStore } from "@/stores/ui-store";

export function Workbench({
  projectId,
  threadId,
  runId,
}: {
  projectId: string;
  threadId: string;
  runId: string | null;
}) {
  useRun(runId);
  const connectionState = useRunStream(runId);
  const inspectorOpen = useUiStore((state) => state.inspectorOpen);

  return (
    <div className="grid h-dvh grid-cols-[auto_minmax(0,1fr)_auto] bg-background">
      <ProjectSidebar projectId={projectId} threadId={threadId} />

      <main className="flex min-w-0 flex-col">
        <Conversation
          runId={runId}
          connectionState={connectionState}
        />
        <Composer
          projectId={projectId}
          threadId={threadId}
          activeRunId={runId}
        />
      </main>

      {inspectorOpen ? <InspectorPanel runId={runId} /> : null}
    </div>
  );
}
```

`Workbench` 不应该知道 API Key、审批具体请求、文件树加载、图节点推断或 Preview URL 拼接。

---

# J. ChatGPT / Codex / Claude 风格的核心交互组件

## J.1 消息不是一段 Markdown，而是一组 Parts

```ts
// frontend/features/chat/types.ts
export type MessagePart =
  | { type: "text"; id: string; text: string }
  | { type: "reasoning-summary"; id: string; text: string }
  | { type: "tool"; id: string; toolCallId: string }
  | { type: "artifact"; id: string; artifactId: string }
  | { type: "plan-review"; id: string; interruptId: string }
  | { type: "error"; id: string; title: string; detail: string };

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  agentId?: string;
  parts: MessagePart[];
  status: "streaming" | "completed" | "failed";
};
```

这样工具调用、Artifact、审批和文本可以按照真实发生顺序嵌入对话，而不是全部塞进右侧抽屉。

## J.2 Message Renderer

```tsx
// frontend/features/chat/message.tsx
import { ArtifactPart } from "./parts/artifact-part";
import { ErrorPart } from "./parts/error-part";
import { PlanReviewPart } from "./parts/plan-review-part";
import { TextPart } from "./parts/text-part";
import { ToolPart } from "./parts/tool-part";
import type { ConversationMessage } from "./types";

export function Message({ message }: { message: ConversationMessage }) {
  return (
    <article
      className="mx-auto w-full max-w-3xl px-5 py-4"
      data-role={message.role}
    >
      <header className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">
          {message.role === "user" ? "You" : message.agentId ?? "PaperPilot"}
        </span>
        {message.status === "streaming" ? (
          <span className="inline-flex items-center gap-1">
            <span className="size-1.5 animate-pulse rounded-full bg-current" />
            Working
          </span>
        ) : null}
      </header>

      <div className="space-y-3">
        {message.parts.map((part) => {
          switch (part.type) {
            case "text":
              return <TextPart key={part.id} text={part.text} />;
            case "tool":
              return (
                <ToolPart
                  key={part.id}
                  toolCallId={part.toolCallId}
                />
              );
            case "artifact":
              return (
                <ArtifactPart
                  key={part.id}
                  artifactId={part.artifactId}
                />
              );
            case "plan-review":
              return (
                <PlanReviewPart
                  key={part.id}
                  interruptId={part.interruptId}
                />
              );
            case "error":
              return (
                <ErrorPart
                  key={part.id}
                  title={part.title}
                  detail={part.detail}
                />
              );
            case "reasoning-summary":
              return (
                <details key={part.id} className="rounded-lg border p-3">
                  <summary className="cursor-pointer text-sm font-medium">
                    Reasoning summary
                  </summary>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {part.text}
                  </p>
                </details>
              );
          }
        })}
      </div>
    </article>
  );
}
```

## J.3 Tool Card：折叠细节，展示真实状态

```tsx
// frontend/features/chat/parts/tool-part.tsx
import {
  CheckCircle2,
  CircleDotDashed,
  Clock3,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useRunTool } from "@/features/runs/selectors";

const icons = {
  proposed: Clock3,
  waiting_approval: Clock3,
  running: CircleDotDashed,
  succeeded: CheckCircle2,
  failed: XCircle,
  rejected: XCircle,
};

export function ToolPart({ toolCallId }: { toolCallId: string }) {
  const tool = useRunTool(toolCallId);
  if (!tool) return null;

  const Icon = icons[tool.state];
  return (
    <Collapsible className="overflow-hidden rounded-xl border bg-card">
      <CollapsibleTrigger className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/40">
        <Icon
          className={
            tool.state === "running"
              ? "size-4 animate-spin"
              : "size-4"
          }
        />
        <span className="min-w-0 flex-1 truncate text-sm font-medium">
          {tool.name}
        </span>
        <Badge variant="outline">{tool.state}</Badge>
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t bg-muted/20">
        <div className="grid gap-3 p-3 text-xs">
          <section>
            <div className="mb-1 font-medium text-muted-foreground">
              Input
            </div>
            <pre className="max-h-56 overflow-auto rounded-md bg-background p-2">
              {JSON.stringify(tool.input, null, 2)}
            </pre>
          </section>
          {Object.keys(tool.output).length > 0 ? (
            <section>
              <div className="mb-1 font-medium text-muted-foreground">
                Output
              </div>
              <pre className="max-h-72 overflow-auto rounded-md bg-background p-2">
                {JSON.stringify(tool.output, null, 2)}
              </pre>
            </section>
          ) : null}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
```

## J.4 Plan Review：用户编辑后发送完整 plan revision

```tsx
// frontend/features/approvals/plan-review-card.tsx
"use client";

import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/http";
import type { EditablePlan, PlanInterrupt } from "./types";

export function PlanReviewCard({
  runId,
  interrupt,
}: {
  runId: string;
  interrupt: PlanInterrupt;
}) {
  const [plan, setPlan] = useState<EditablePlan>(interrupt.plan);
  const [feedback, setFeedback] = useState("");

  const resume = useMutation({
    mutationFn: (body: object) =>
      api.post(`/api/v2/runs/${runId}/resume`, body),
  });

  function toggleStep(stepId: string, enabled: boolean) {
    setPlan((current) => ({
      ...current,
      revision: current.revision + 1,
      steps: current.steps.map((step) =>
        step.id === stepId ? { ...step, enabled } : step,
      ),
    }));
  }

  const isValid = useMemo(
    () => plan.steps.some((step) => step.enabled),
    [plan.steps],
  );

  return (
    <section className="rounded-xl border bg-card p-4 shadow-sm">
      <div className="mb-3">
        <h3 className="text-sm font-semibold">Review execution plan</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Disabled steps will not be executed. Changes create a new plan revision.
        </p>
      </div>

      <div className="space-y-2">
        {plan.steps.map((step, index) => (
          <label
            key={step.id}
            className="flex gap-3 rounded-lg border p-3 hover:bg-muted/30"
          >
            <Checkbox
              checked={step.enabled}
              onCheckedChange={(checked) =>
                toggleStep(step.id, checked === true)
              }
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  {index + 1}
                </span>
                <span className="text-sm font-medium">{step.title}</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {step.description}
              </p>
            </div>
          </label>
        ))}
      </div>

      <Textarea
        className="mt-3"
        placeholder="Optional feedback for the agent"
        value={feedback}
        onChange={(event) => setFeedback(event.target.value)}
      />

      <div className="mt-3 flex justify-end gap-2">
        <Button
          variant="ghost"
          disabled={resume.isPending}
          onClick={() =>
            resume.mutate({
              interrupt_id: interrupt.id,
              value: { action: "reject", feedback },
            })
          }
        >
          Reject
        </Button>
        <Button
          disabled={!isValid || resume.isPending}
          onClick={() =>
            resume.mutate({
              interrupt_id: interrupt.id,
              value: {
                action:
                  plan.revision === interrupt.plan.revision
                    ? "approve"
                    : "edit",
                plan,
                feedback,
              },
            })
          }
        >
          {resume.isPending ? "Resuming…" : "Approve and continue"}
        </Button>
      </div>
    </section>
  );
}
```

## J.5 Composer：发送、停止、附件、模式选择

```tsx
// frontend/features/chat/composer.tsx
"use client";

import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowUp, Paperclip, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/http";

export function Composer({
  projectId,
  threadId,
  activeRunId,
}: {
  projectId: string;
  threadId: string;
  activeRunId: string | null;
}) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"reproduce" | "productize">("productize");
  const [fileIds, setFileIds] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const startRun = useMutation({
    mutationFn: () =>
      api.post<{ run_id: string }>("/api/v2/runs", {
        project_id: projectId,
        thread_id: threadId,
        mode,
        task: text.trim(),
        file_ids: fileIds,
        model_profile_id: "default",
      }),
    onSuccess: () => {
      setText("");
      setFileIds([]);
    },
  });

  const cancelRun = useMutation({
    mutationFn: () =>
      api.post(`/api/v2/runs/${activeRunId}/cancel`, {}),
  });

  const running = Boolean(activeRunId);

  return (
    <div className="border-t bg-background/90 px-4 py-3 backdrop-blur">
      <div className="mx-auto max-w-3xl rounded-2xl border bg-card shadow-sm focus-within:ring-1 focus-within:ring-ring">
        <Textarea
          ref={textareaRef}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              if (text.trim() && !startRun.isPending && !running) {
                startRun.mutate();
              }
            }
          }}
          placeholder="Ask PaperPilot to turn a paper into a product…"
          className="min-h-24 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
        />

        <div className="flex items-center justify-between gap-2 px-2 pb-2">
          <div className="flex items-center gap-1">
            <Button size="icon" variant="ghost" aria-label="Attach paper">
              <Paperclip className="size-4" />
            </Button>
            <select
              value={mode}
              onChange={(event) =>
                setMode(event.target.value as typeof mode)
              }
              className="h-8 rounded-md border bg-background px-2 text-xs"
              disabled={running}
            >
              <option value="productize">Productize</option>
              <option value="reproduce">Reproduce</option>
            </select>
          </div>

          {running ? (
            <Button
              size="icon"
              variant="secondary"
              aria-label="Stop run"
              onClick={() => cancelRun.mutate()}
            >
              <Square className="size-3.5 fill-current" />
            </Button>
          ) : (
            <Button
              size="icon"
              disabled={!text.trim() || startRun.isPending}
              aria-label="Send"
              onClick={() => startRun.mutate()}
            >
              <ArrowUp className="size-4" />
            </Button>
          )}
        </div>
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
        Generated code and commands must still pass verification and approval.
      </p>
    </div>
  );
}
```

## J.6 Inspector 不是状态真相，只是 Artifact 视图

右栏推荐四个 Tab：

```text
Preview | Artifacts | Code | Graph
```

- `Preview`：真实容器预览，不显示伪造阶段列表；
- `Artifacts`：PRD、Capability Map、Evaluation、Logs；
- `Code`：文件树、Monaco、Diff、保存 Patch；
- `Graph`：调试视图，节点状态直接来自 graph event，不通过文本猜测。

当没有 Preview 时，显示明确状态：

```tsx
<EmptyState
  title="Preview is not running"
  description="A preview becomes available after the generated app passes install and build checks."
/>
```

不要显示固定的：

```text
✓ Paper uploaded
✓ Capability card
✓ PRD
✓ App generated
✓ Verified
○ Done
```

除非每一项都由对应的服务端事件和 Artifact 证明。


---

# K. 密钥、文件与命令安全：对当前代码的直接替换

## K.1 API Key 接口必须只返回掩码和是否已配置

当前 `GET /api/llm/config` 直接返回 `api_key`，前端 `ApiLlmConfig` 也把它定义成完整字符串，并且 Run Create/Proposal Execute 请求仍允许携带 key。建议改为 profile + secret reference。

```python
# backend/schemas/model_profile.py
from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr


class ModelProfileRead(BaseModel):
    id: str
    name: str
    provider: str
    base_url: str
    model: str
    implementation_model: str
    has_api_key: bool
    api_key_hint: str | None = None


class ModelProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    provider: str
    base_url: str
    model: str
    implementation_model: str = ""
    api_key: SecretStr | None = None
```

```python
# backend/services/secret_service.py
from __future__ import annotations

import keyring

SERVICE_NAME = "paperpilot"


class SecretService:
    def set_model_key(self, profile_id: str, api_key: str) -> None:
        if not api_key.strip():
            raise ValueError("API key cannot be empty")
        keyring.set_password(SERVICE_NAME, f"model:{profile_id}", api_key)

    def get_model_key(self, profile_id: str) -> str | None:
        return keyring.get_password(SERVICE_NAME, f"model:{profile_id}")

    def delete_model_key(self, profile_id: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, f"model:{profile_id}")
        except keyring.errors.PasswordDeleteError:
            pass

    def hint(self, profile_id: str) -> str | None:
        value = self.get_model_key(profile_id)
        if not value:
            return None
        return f"••••{value[-4:]}" if len(value) >= 4 else "••••"
```

服务端无系统 keyring 时，可使用加密数据库字段，但主密钥必须来自环境变量或 KMS，不能再写进仓库目录。

```python
# backend/routers/model_profiles.py
@router.get("/{profile_id}", response_model=ModelProfileRead)
def get_profile(profile_id: str, session: Session = Depends(get_session)):
    profile = profile_repository.get(session, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ModelProfileRead(
        id=profile.id,
        name=profile.name,
        provider=profile.provider,
        base_url=profile.base_url,
        model=profile.model,
        implementation_model=profile.implementation_model,
        has_api_key=secret_service.get_model_key(profile.id) is not None,
        api_key_hint=secret_service.hint(profile.id),
    )
```

前端类型应删除 `api_key: string`：

```ts
export type ModelProfile = {
  id: string;
  name: string;
  provider: string;
  baseUrl: string;
  model: string;
  implementationModel: string;
  hasApiKey: boolean;
  apiKeyHint: string | null;
};
```

## K.2 文件路径必须以 Artifact/File ID 为入口

当前很多 API 接受 `pdf_path`、`cwd`、`path`。即便使用 `resolve_allowed_path`，把宿主路径暴露给前端仍会扩大攻击面。推荐：

```python
# backend/services/file_locator.py
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from backend.db.models import ArtifactModel


class FileLocator:
    def __init__(self, storage_root: Path) -> None:
        self.storage_root = storage_root.resolve()

    def artifact_path(self, session: Session, artifact_id: str) -> Path:
        artifact = session.get(ArtifactModel, artifact_id)
        if artifact is None:
            raise LookupError("Artifact not found")

        path = (self.storage_root / artifact.storage_path).resolve()
        if not path.is_relative_to(self.storage_root):
            raise ValueError("Artifact escaped storage root")
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
```

前端创建 Run 时只传 `file_ids`，后端在 worker 内解析真实路径。

## K.3 上传流式写盘、魔数校验与配额

```python
# backend/routers/uploads_v2.py
from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import magic
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/api/v2/files", tags=["files-v2"])

MAX_PDF_BYTES = 80 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
ALLOWED_MIME = {"application/pdf"}


@router.post("")
async def upload_file(file: UploadFile = File(...)) -> dict[str, object]:
    file_id = f"file_{uuid4().hex}"
    target = upload_root / f"{file_id}.pdf"
    temp = target.with_suffix(".upload")
    digest = hashlib.sha256()
    total = 0
    header = bytearray()

    try:
        with temp.open("wb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                total += len(chunk)
                if total > MAX_PDF_BYTES:
                    raise HTTPException(status_code=413, detail="PDF too large")
                if len(header) < 8192:
                    header.extend(chunk[: 8192 - len(header)])
                digest.update(chunk)
                output.write(chunk)

        mime = magic.from_buffer(bytes(header), mime=True)
        if mime not in ALLOWED_MIME or not bytes(header).startswith(b"%PDF-"):
            raise HTTPException(status_code=415, detail="Invalid PDF file")

        temp.replace(target)
        return {
            "file_id": file_id,
            "size_bytes": total,
            "sha256": digest.hexdigest(),
            "mime_type": mime,
        }
    finally:
        await file.close()
        if temp.exists():
            temp.unlink(missing_ok=True)
```

还应增加：

- 每项目总容量配额；
- 每用户并发上传数；
- PDF 页数上限；
- 解压缩炸弹和嵌入文件检查；
- 上传后异步恶意文件扫描；
- 原始文件只读保存，不在原文件上写修改。

## K.4 GitHub URL 解析与 SSRF 防护

```python
# backend/security/github_url.py
from __future__ import annotations

import re
from urllib.parse import urlparse

GITHUB_RE = re.compile(
    r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}(?:\.git)?$"
)


def normalize_github_repo_url(raw: str) -> str:
    parsed = urlparse(raw.strip())
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise ValueError("Only https://github.com repositories are allowed")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Credentials and custom ports are not allowed")

    repo = parsed.path.strip("/")
    if not GITHUB_RE.fullmatch(repo):
        raise ValueError("Invalid GitHub owner/repository path")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"https://github.com/{repo}.git"
```

Clone 时：

```python
argv = [
    "git",
    "clone",
    "--depth=1",
    "--filter=blob:none",
    "--no-tags",
    normalized_url,
    "/workspace/repo",
]
```

同时配置：

- clone 超时；
- 仓库最大磁盘体积；
- 禁用 submodule 自动初始化；
- 不执行 Git hooks；
- 不自动运行仓库中的安装脚本；
- LFS 单独审批；
- 私有仓库 token 使用短期 secret mount，不写入 remote URL。

---

# L. Reproduce Agent：针对当前 Graph 的深层修改

## L.1 不再硬编码 `main.py + requirements.txt + tests/test_smoke.py`

当前 `_build_implementation_contract()` 固定：

```text
README.md
main.py
requirements.txt
tests/test_smoke.py
python main.py --smoke-test
```

这会把不同论文仓库强行压成同一结构。对于 Hydra、Lightning、MMEngine、HuggingFace、Next.js Demo 等项目都不合适。

应先生成 `RepositoryIndex`：

```python
# schemas/repository_index.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Entrypoint(BaseModel):
    path: str
    kind: Literal["train", "evaluate", "inference", "demo", "test", "unknown"]
    command: list[str]
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)


class DependencySpec(BaseModel):
    path: str
    ecosystem: Literal["pip", "conda", "poetry", "npm", "other"]


class RepositoryIndex(BaseModel):
    languages: dict[str, int]
    dependency_specs: list[DependencySpec]
    config_files: list[str]
    checkpoints: list[str]
    dataset_references: list[str]
    entrypoints: list[Entrypoint]
    framework_markers: list[str]
    test_commands: list[list[str]]
    unresolved_questions: list[str]
```

## L.2 使用 AST 和配置扫描，不只依赖 LLM 阅读 README

```python
# tools/repository_indexer.py
from __future__ import annotations

import ast
import json
from pathlib import Path

from schemas.repository_index import DependencySpec, Entrypoint, RepositoryIndex


ENTRYPOINT_NAMES = {
    "train.py": "train",
    "eval.py": "evaluate",
    "evaluate.py": "evaluate",
    "infer.py": "inference",
    "inference.py": "inference",
    "demo.py": "demo",
    "app.py": "demo",
    "test.py": "test",
}


def python_has_main(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        source = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
        if "__name__" in source and "__main__" in source:
            return True
    return False


def build_repository_index(root: Path) -> RepositoryIndex:
    root = root.resolve()
    entrypoints: list[Entrypoint] = []
    dependencies: list[DependencySpec] = []
    configs: list[str] = []
    frameworks: set[str] = set()
    language_counts: dict[str, int] = {}

    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        language_counts[path.suffix] = language_counts.get(path.suffix, 0) + 1

        if path.name == "requirements.txt":
            dependencies.append(DependencySpec(path=relative, ecosystem="pip"))
        elif path.name in {"environment.yml", "environment.yaml"}:
            dependencies.append(DependencySpec(path=relative, ecosystem="conda"))
        elif path.name == "pyproject.toml":
            dependencies.append(DependencySpec(path=relative, ecosystem="poetry"))
        elif path.name == "package.json":
            dependencies.append(DependencySpec(path=relative, ecosystem="npm"))

        if path.suffix in {".yaml", ".yml", ".json", ".toml"}:
            configs.append(relative)

        if path.suffix == ".py" and python_has_main(path):
            kind = ENTRYPOINT_NAMES.get(path.name, "unknown")
            entrypoints.append(
                Entrypoint(
                    path=relative,
                    kind=kind,
                    command=["python", relative],
                    confidence=0.9 if kind != "unknown" else 0.6,
                    evidence=["Python __main__ guard"],
                )
            )

        if path.name == "package.json":
            try:
                package = json.loads(path.read_text(encoding="utf-8"))
                scripts = package.get("scripts", {})
                if "next" in json.dumps(package).lower():
                    frameworks.add("nextjs")
                for name in ("dev", "build", "test"):
                    if name in scripts:
                        entrypoints.append(
                            Entrypoint(
                                path=relative,
                                kind="test" if name == "test" else "demo",
                                command=["npm", "run", name],
                                confidence=0.95,
                                evidence=[f"package.json scripts.{name}"],
                            )
                        )
            except (OSError, json.JSONDecodeError):
                pass

    return RepositoryIndex(
        languages=language_counts,
        dependency_specs=dependencies,
        config_files=configs[:500],
        checkpoints=[],
        dataset_references=[],
        entrypoints=entrypoints,
        framework_markers=sorted(frameworks),
        test_commands=[item.command for item in entrypoints if item.kind == "test"],
        unresolved_questions=[],
    )
```

## L.3 Evidence 必须带定位，不只是 summary 字符串

```python
# schemas/evidence.py
class EvidenceRef(BaseModel):
    source: Literal["paper", "repository", "user"]
    source_id: str
    locator: str  # page 4, section 3.2, path:line range
    quote: str
    interpretation: str
    confidence: float = Field(ge=0, le=1)


class RequirementWithEvidence(BaseModel):
    value: str
    evidence: list[EvidenceRef]
    status: Literal["confirmed", "inferred", "missing"]
```

例如 Dataset 不是简单写：

```json
{"name": "CIFAR-10", "confidence": "high"}
```

而应写：

```json
{
  "value": "CIFAR-10",
  "status": "confirmed",
  "evidence": [
    {
      "source": "paper",
      "source_id": "paper_1",
      "locator": "page 6, section 4.1",
      "quote": "Experiments are conducted on CIFAR-10...",
      "interpretation": "Primary benchmark dataset",
      "confidence": 0.98
    }
  ]
}
```

## L.4 Implementation Contract 根据证据生成

```python
# services/implementation_contract_builder.py
from __future__ import annotations

from schemas.repository_index import RepositoryIndex
from schemas.reproduction_schema import ImplementationContract, ReproductionPlan


def build_contract(
    plan: ReproductionPlan,
    index: RepositoryIndex,
) -> ImplementationContract:
    required_files = ["README.md"]
    required_cli: list[str] = []
    required_tests: list[str] = []

    selected_entrypoints = [
        item for item in index.entrypoints
        if item.kind in {"inference", "demo", "evaluate", "test"}
    ]

    if selected_entrypoints:
        required_cli.extend(" ".join(item.command) for item in selected_entrypoints[:3])
    else:
        # 只有 paper-only 且必须生成新实现时，才引入统一 CLI。
        required_files.extend(["src/__init__.py", "src/main.py"])
        required_cli.append("python -m src.main --help")

    for command in index.test_commands[:3]:
        required_tests.append(" ".join(command))

    if not required_tests:
        required_tests.append("python -m pytest -q")

    return ImplementationContract(
        task_name=plan.goal,
        input_schema=plan.input_schema,
        output_schema=plan.output_schema,
        required_modules=plan.architecture_plan,
        required_files=required_files,
        required_cli=required_cli,
        required_tests=required_tests,
        smoke_test_command=required_cli[0],
        non_goals=plan.fallback_plan,
        evidence_links=plan.acceptance_criteria + plan.validation_plan,
        forbidden_patterns=[
            "guaranteed SOTA",
            "fully reproduces",
            "production ready",
        ],
    )
```

## L.5 代码生成采用 Patch Loop，而不是每轮全量重写

```python
# schemas/patch_bundle.py
class FilePatch(BaseModel):
    path: str
    operation: Literal["create", "update", "delete"]
    unified_diff: str
    reason: str
    fixes_issue_ids: list[str]


class PatchBundle(BaseModel):
    base_revision: str
    patches: list[FilePatch]
```

```python
# tools/patch_applier.py
from __future__ import annotations

import subprocess
from pathlib import Path

from schemas.patch_bundle import PatchBundle


def apply_patch_bundle(workspace: Path, bundle: PatchBundle) -> None:
    patch_text = "\n".join(patch.unified_diff for patch in bundle.patches)
    process = subprocess.run(
        ["git", "apply", "--check", "-"],
        input=patch_text,
        text=True,
        cwd=workspace,
        capture_output=True,
        timeout=20,
        check=False,
    )
    if process.returncode != 0:
        raise ValueError(f"Patch check failed: {process.stderr}")

    process = subprocess.run(
        ["git", "apply", "-"],
        input=patch_text,
        text=True,
        cwd=workspace,
        capture_output=True,
        timeout=20,
        check=False,
    )
    if process.returncode != 0:
        raise ValueError(f"Patch apply failed: {process.stderr}")
```

注意：Patch 仍然只能在容器化 workspace 内应用；当前 `PatchService` 直接写宿主文件并且 Python 语法失败后仍标记 `applied=True`，建议改为先临时文件校验，再原子替换。

```python
# backend/services/safe_patch_service.py（关键部分）
import os
import tempfile


def atomic_write_validated(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=target.parent, prefix=".patch-")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        validate_file(temp_path, expected_suffix=target.suffix)
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)
```

---

# M. Productize Agent：从论文 Idea 到真实产品的改造

## M.1 Productize 应分成 5 个独立合同

```text
1. Capability Contract
   论文真正提供什么能力，输入输出、依赖、限制和证据是什么

2. Product Opportunity Contract
   目标用户、JTBD、使用频率、价值、不可做的声明

3. App Contract
   页面、交互、API、数据结构、错误状态、验收测试

4. Adapter Contract
   原始研究代码如何被封装；真实模式、mock fallback 和 unsupported 的边界

5. Verification Contract
   build、unit test、browser test、adapter smoke test、safety check
```

不要让 `ProductPlan` 同时承担所有信息。

## M.2 Capability Contract

```python
# schemas/capability_contract.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from schemas.evidence import EvidenceRef


class IOField(BaseModel):
    name: str
    type: str
    required: bool = True
    description: str
    examples: list[str] = Field(default_factory=list)


class CapabilityContract(BaseModel):
    id: str
    name: str
    summary: str
    inputs: list[IOField]
    outputs: list[IOField]
    execution_kind: Literal[
        "local_model",
        "remote_api",
        "algorithm",
        "analysis_only",
        "unknown",
    ]
    repository_entrypoint: list[str] | None = None
    checkpoint_requirements: list[str] = Field(default_factory=list)
    hardware_requirements: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    readiness: Literal["ready", "partial", "blocked", "unknown"]
```

如果 `readiness=blocked`，Productize 不应伪装成真实推理；UI 必须明确展示“Demo data only / adapter unavailable”。

## M.3 Adapter Contract 和真正的 fallback

```python
# schemas/adapter_contract.py
class AdapterContract(BaseModel):
    name: str
    input_schema: dict
    output_schema: dict
    real_mode: bool
    mock_fallback: bool
    health_check: str
    invoke_command: list[str] | None
    unsupported_reason: str | None = None
```

生成项目的 Adapter：

```ts
// generated-app/lib/research-adapter.ts
import { z } from "zod";

const inputSchema = z.object({
  imageBase64: z.string().min(1),
  threshold: z.number().min(0).max(1).default(0.5),
});

const outputSchema = z.object({
  predictions: z.array(
    z.object({
      label: z.string(),
      score: z.number(),
    }),
  ),
  mode: z.enum(["real", "mock"]),
  warnings: z.array(z.string()),
});

export type ResearchInput = z.infer<typeof inputSchema>;
export type ResearchOutput = z.infer<typeof outputSchema>;

export async function runResearchAdapter(
  rawInput: unknown,
): Promise<ResearchOutput> {
  const input = inputSchema.parse(rawInput);
  const endpoint = process.env.RESEARCH_ADAPTER_URL;

  if (!endpoint) {
    if (process.env.ALLOW_MOCK_FALLBACK !== "true") {
      throw new Error("Research adapter is not configured");
    }
    return outputSchema.parse({
      predictions: [
        { label: "example", score: 0.82 },
      ],
      mode: "mock",
      warnings: [
        "This result is generated by a deterministic demo adapter, not the paper model.",
      ],
    });
  }

  const response = await fetch(`${endpoint}/predict`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
    signal: AbortSignal.timeout(60_000),
  });
  if (!response.ok) {
    throw new Error(`Research adapter failed: ${response.status}`);
  }
  return outputSchema.parse(await response.json());
}
```

这里 mock 是明确的 fallback，不是产品默认永久运行模式。

## M.4 PRD 必须可测试

```python
# schemas/app_contract.py
class AcceptanceScenario(BaseModel):
    id: str
    given: list[str]
    when: list[str]
    then: list[str]
    priority: Literal["must", "should", "could"]


class AppContract(BaseModel):
    product_name: str
    primary_user: str
    primary_job: str
    routes: list[RouteContract]
    api_routes: list[ApiRouteContract]
    data_models: list[DataModelContract]
    error_states: list[str]
    empty_states: list[str]
    loading_states: list[str]
    acceptance_scenarios: list[AcceptanceScenario]
```

示例：

```json
{
  "id": "scenario_primary_upload",
  "given": [
    "the user opens the home page",
    "the adapter health check passes"
  ],
  "when": [
    "the user uploads a valid PNG",
    "the user clicks Analyze"
  ],
  "then": [
    "the page shows an in-progress state",
    "the result card displays predictions",
    "the result identifies whether real or mock mode was used"
  ],
  "priority": "must"
}
```

这些 scenario 直接转换为 Playwright 测试，而不是只保存在 PRD 文本中。

## M.5 Productize Graph 新流程

```text
parse_papers
  → extract_capabilities
  → validate_capability_evidence
  → propose_opportunities
  → [human selects opportunity]
  → build_app_contract
  → [human edits/approves contract]
  → inspect_repo_for_adapter
  → build_adapter_contract
  → generate_next_app
  → npm_install
  → next_build
  → unit_test
  → browser_test
  → adapter_smoke_test
  → repair_by_typed_issue (max 3)
  → create_preview
  → final_evaluation
```

最终成功必须满足：

```python
def product_is_deliverable(state: dict) -> bool:
    return all(
        [
            state["build_report"]["passed"],
            state["unit_test_report"]["passed"],
            state["browser_test_report"]["passed"],
            state["contract_report"]["passed"],
            (
                state["adapter_report"]["passed"]
                or state["adapter_contract"]["mock_fallback"]
            ),
        ]
    )
```

不能再用 evaluator 的单个 `overall_score >= 4.0` 代表“产品可用”。


---

# N. 自动化测试：专门覆盖当前最容易复现的 Bug

## N.1 后端：重启后 Run 不应自动失败

当前 `_recover_stale_running_runs()` 会把所有 `running` Run 标记失败。改造后应测试 worker 可以依据 checkpoint 恢复，或至少回到 queued 等待重新领取。

```python
# tests/backend/test_run_recovery.py
from backend.db.models import RunModel, RunStatus
from backend.workers.recovery import recover_incomplete_runs


def test_running_run_is_requeued_when_checkpoint_exists(
    session,
    checkpoint_store,
):
    run = RunModel(
        id="run_recoverable",
        project_id="project_1",
        thread_id="thread_1",
        mode="productize",
        status=RunStatus.RUNNING.value,
        task="Build an app",
        input_json={},
        checkpoint_thread_id="checkpoint:run_recoverable",
    )
    session.add(run)
    session.commit()
    checkpoint_store.seed("checkpoint:run_recoverable", next_node="generate_app")

    recovered = recover_incomplete_runs(session, checkpoint_store)

    session.refresh(run)
    assert recovered == ["run_recoverable"]
    assert run.status == RunStatus.QUEUED.value
    assert run.error_json == {}
```

```python
# backend/workers/recovery.py
from sqlalchemy import select

from backend.db.models import RunModel, RunStatus


def recover_incomplete_runs(session, checkpoint_store) -> list[str]:
    runs = session.scalars(
        select(RunModel).where(
            RunModel.status.in_(
                [RunStatus.RUNNING.value, RunStatus.QUEUED.value]
            )
        )
    ).all()

    recovered: list[str] = []
    for run in runs:
        if checkpoint_store.exists(run.checkpoint_thread_id):
            run.status = RunStatus.QUEUED.value
            recovered.append(run.id)
        else:
            run.status = RunStatus.FAILED.value
            run.error_json = {
                "code": "checkpoint_missing",
                "message": "Run could not be recovered because its checkpoint is missing.",
            }
    session.commit()
    return recovered
```

## N.2 后端：Event sequence 必须单调且唯一

```python
# tests/backend/test_event_repository.py
from concurrent.futures import ThreadPoolExecutor

from backend.repositories.events import EventRepository


def test_event_sequence_is_monotonic(session_factory, seeded_run):
    repository = EventRepository()

    def append(index: int) -> int:
        with session_factory() as session:
            run = session.get(type(seeded_run), seeded_run.id)
            event = repository.append(
                session,
                run=run,
                event_type="test.event",
                payload={"index": index},
            )
            session.commit()
            return event.sequence

    with ThreadPoolExecutor(max_workers=4) as pool:
        sequences = list(pool.map(append, range(20)))

    assert sorted(sequences) == list(range(1, 21))
    assert len(set(sequences)) == 20
```

SQLite 并发测试可能需要串行写锁；PostgreSQL 用 `SELECT FOR UPDATE` 可保证正确性。

## N.3 后端：计划编辑必须影响 Graph State

```python
# tests/backend/test_plan_resume.py
from langgraph.types import Command


def test_edited_plan_is_used_after_resume(compiled_graph, graph_config):
    initial = {
        "editable_plan": {
            "revision": 1,
            "objective": "Build demo",
            "steps": [
                {
                    "id": "generate",
                    "title": "Generate app",
                    "description": "Create application",
                    "agent": "generator",
                    "enabled": True,
                    "depends_on": [],
                    "acceptance_criteria": [],
                    "risk": "low",
                },
                {
                    "id": "train",
                    "title": "Train model",
                    "description": "Expensive training",
                    "agent": "trainer",
                    "enabled": True,
                    "depends_on": [],
                    "acceptance_criteria": [],
                    "risk": "high",
                },
            ],
        }
    }

    compiled_graph.invoke(initial, config=graph_config)
    snapshot = compiled_graph.get_state(graph_config)
    assert snapshot.next

    edited = initial["editable_plan"] | {
        "revision": 2,
        "steps": [
            initial["editable_plan"]["steps"][0],
            initial["editable_plan"]["steps"][1] | {"enabled": False},
        ],
    }
    compiled_graph.invoke(
        Command(
            resume={
                "action": "edit",
                "plan": edited,
                "feedback": "Do not train the model",
            }
        ),
        config=graph_config,
    )

    resumed = compiled_graph.get_state(graph_config)
    assert resumed.values["editable_plan"]["revision"] == 2
    assert resumed.values["editable_plan"]["steps"][1]["enabled"] is False
```

## N.4 后端：审批拒绝后工具不能执行

```python
# tests/backend/test_tool_approval.py
from langgraph.types import Command


def test_rejected_command_is_never_executed(
    command_graph,
    graph_config,
    fake_runner,
):
    command_graph.invoke(
        {
            "pending_tool_request": {
                "id": "tool_1",
                "name": "run_command",
                "risk": "high",
                "input": {"argv": ["python", "train.py"]},
            }
        },
        config=graph_config,
    )

    command_graph.invoke(
        Command(
            resume={
                "action": "reject",
                "feedback": "Training is outside MVP scope",
            }
        ),
        config=graph_config,
    )

    assert fake_runner.calls == []
    snapshot = command_graph.get_state(graph_config)
    assert snapshot.values["tool_result"]["executed"] is False
```

## N.5 后端：API Key 永远不出现在响应和 Run JSON 中

```python
# tests/backend/test_secret_redaction.py

def test_model_profile_does_not_return_key(client, secret_service):
    secret_service.set_model_key("default", "sk-super-secret-value")

    response = client.get("/api/v2/model-profiles/default")

    assert response.status_code == 200
    payload = response.json()
    assert "api_key" not in payload
    assert payload["has_api_key"] is True
    assert payload["api_key_hint"] == "••••alue"
    assert "sk-super-secret-value" not in response.text


def test_run_input_does_not_store_key(client, session):
    response = client.post(
        "/api/v2/runs",
        json={
            "project_id": "p1",
            "thread_id": "t1",
            "mode": "productize",
            "task": "Build app",
            "file_ids": ["file_1"],
            "model_profile_id": "default",
        },
    )
    assert response.status_code == 202
    run = session.get(RunModel, response.json()["run_id"])
    assert "api_key" not in run.input_json
```

## N.6 后端：Path Traversal

```python
# tests/backend/test_generated_path_security.py
import pytest

from productize.next_app_writer import validate_generated_path


@pytest.mark.parametrize(
    "path",
    [
        "../../etc/passwd",
        "/etc/passwd",
        "app/../../../secret",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        ".git/config",
        "unknown-root/file.ts",
    ],
)
def test_generated_path_rejects_escape(path: str):
    with pytest.raises(ValueError):
        validate_generated_path(path)
```

## N.7 后端：Sandbox 不能读取宿主敏感文件

```python
# tests/integration/test_docker_sandbox.py
from backend.runtime.docker_runner import ContainerLimits


def test_sandbox_cannot_read_host_etc_passwd(docker_runner, workspace):
    result = docker_runner.run(
        source_dir=workspace,
        image="python:3.12-alpine@sha256:<PINNED_DIGEST>",
        argv=[
            "python",
            "-c",
            "from pathlib import Path; print(Path('/etc/passwd').read_text())",
        ],
        limits=ContainerLimits(network_enabled=False),
    )

    # 容器内可能有自己的 /etc/passwd，但不能包含宿主用户或项目路径。
    assert "/home/jiangwenhan" not in result.stdout
    assert str(workspace) not in result.stdout
```

## N.8 前端：乱序旧事件不能覆盖新状态

```ts
// frontend/features/runs/event-reducer.test.ts
import { describe, expect, it } from "vitest";

import { applyRunEvent } from "./event-reducer";
import { emptyRunState } from "./test-fixtures";

describe("applyRunEvent", () => {
  it("ignores duplicate and out-of-order events", () => {
    const running = applyRunEvent(emptyRunState("run_1"), {
      type: "run.state",
      eventId: "evt_10",
      runId: "run_1",
      sequence: 10,
      status: "running",
      nodeId: "generate",
      summary: "Generating",
      createdAt: "2026-07-14T00:00:00Z",
    });

    const stale = applyRunEvent(running, {
      type: "run.state",
      eventId: "evt_9",
      runId: "run_1",
      sequence: 9,
      status: "queued",
      nodeId: null,
      summary: "Queued",
      createdAt: "2026-07-13T23:59:59Z",
    });

    expect(stale).toBe(running);
    expect(stale.status).toBe("running");
    expect(stale.lastSequence).toBe(10);
  });

  it("concatenates streaming text deltas", () => {
    let state = emptyRunState("run_1");
    state = applyRunEvent(state, {
      type: "message.started",
      eventId: "evt_1",
      runId: "run_1",
      sequence: 1,
      messageId: "msg_1",
      role: "assistant",
      agentId: "planner",
      createdAt: "2026-07-14T00:00:00Z",
    });
    state = applyRunEvent(state, {
      type: "message.delta",
      eventId: "evt_2",
      runId: "run_1",
      sequence: 2,
      messageId: "msg_1",
      delta: "Hello ",
      createdAt: "2026-07-14T00:00:01Z",
    });
    state = applyRunEvent(state, {
      type: "message.delta",
      eventId: "evt_3",
      runId: "run_1",
      sequence: 3,
      messageId: "msg_1",
      delta: "world",
      createdAt: "2026-07-14T00:00:02Z",
    });

    expect(state.messages.msg_1.content).toBe("Hello world");
  });
});
```

## N.9 Playwright：刷新后继续看到流式输出

```ts
// frontend/e2e/run-reconnect.spec.ts
import { expect, test } from "@playwright/test";

test("refresh reconnects to an active run without losing messages", async ({ page }) => {
  await page.goto("/projects/p1/threads/t1");
  await page.getByPlaceholder(/Ask PaperPilot/i).fill(
    "Build a minimal app from this paper",
  );
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Working")).toBeVisible();
  await expect(page.locator("article[data-role='assistant']")).toContainText(
    /plan|analy/i,
    { timeout: 20_000 },
  );

  await page.reload();

  await expect(page.getByText(/Connected|Working/)).toBeVisible();
  const assistant = page.locator("article[data-role='assistant']").last();
  const before = await assistant.textContent();

  await expect
    .poll(async () => assistant.textContent(), { timeout: 20_000 })
    .not.toBe(before);
});
```

## N.10 Playwright：右侧 Preview 状态必须与真实事件一致

```ts
// frontend/e2e/preview-truthfulness.spec.ts
import { expect, test } from "@playwright/test";

test("preview is unavailable before successful build", async ({ page }) => {
  await page.goto("/projects/p1/threads/t1?run=run_building");
  await page.getByRole("tab", { name: "Preview" }).click();

  await expect(page.getByText("Preview is not running")).toBeVisible();
  await expect(page.locator("iframe")).toHaveCount(0);
});

test("preview iframe appears only after preview.created event", async ({ page }) => {
  await page.goto("/projects/p1/threads/t1?run=run_ready");
  await page.getByRole("tab", { name: "Preview" }).click();

  const frame = page.locator("iframe[title='Generated app preview']");
  await expect(frame).toBeVisible();
  await expect(frame).toHaveAttribute("src", /\/api\/previews\/preview_/);
});
```

---

# O. 按当前文件执行的修改清单

## O.1 第一批 PR：修复真实性与安全

### PR 1：`security/model-profile-secret-store`

**删除或停止使用：**

```text
backend/routers/llm.py 中 LLM_CONFIG_FILE 明文逻辑
frontend/lib/api.ts 中 ApiLlmConfig.api_key 回读
RunCreateRequest.api_key
ApiProductizeProposalExecuteRequest.api_key
```

**新增：**

```text
backend/db/models/model_profile.py
backend/services/secret_service.py
backend/routers/model_profiles.py
frontend/features/settings/model-profiles-api.ts
frontend/features/settings/model-profile-form.tsx
```

验收：浏览器 Network、Run JSON、日志、`workspace/` 和仓库根目录都搜不到完整 key。

### PR 2：`runtime/containerized-command-runner`

**替换：**

```text
tools/command_runner.py::run_command_sandbox
tools/command_runner.py::_run_command_in_existing_sandbox
tools/command_runner.py::run_sandbox_verification
```

**新增：**

```text
backend/runtime/docker_runner.py
backend/runtime/build_pipeline.py
backend/runtime/images/
tests/integration/test_docker_sandbox.py
```

验收：依赖安装、构建和 smoke test 不改变宿主 Python/npm 环境。

### PR 3：`bug/patch-atomic-validation`

**修改：**

```text
backend/services/patch_service.py::apply_patch
```

当前语法失败仍写入文件并返回 `applied=True`。应改成：临时文件 → 校验 → 原子替换 → 更新状态。

## O.2 第二批 PR：Durable Run 与增量流

### PR 4：`architecture/durable-run-store`

**逐步替换：**

```text
backend/services/run_service.py
backend/services/event_service.py
backend/services/command_service.py 中 _results 内存存储
backend/services/patch_service.py 中 _patches 内存存储
pipeline/graph_checkpointer.py 中 InMemorySaver
```

**不要一次删完。迁移顺序：**

1. 引入 DB models 和 repository；
2. Run 创建双写 DB + 旧 JSON；
3. 读路径切到 DB；
4. 事件切 DB sequence；
5. 停止写旧 JSON/JSONL；
6. 删除 `InMemoryRunService`。

### PR 5：`streaming/sequenced-sse`

**新增：**

```text
GET /api/v2/runs/{run_id}/snapshot
GET /api/v2/runs/{run_id}/events/stream
frontend/features/runs/event-reducer.ts
frontend/features/runs/use-run-stream.ts
```

**移除 WorkspaceShell 中：**

```text
每个 WebSocket message 后 Promise.all(refreshRun, refreshGraph, ...)
轮询式 refreshCompanion
仅恢复 running run 的 sessionStorage 逻辑
clearStaleRun 后回填 mock plan 的逻辑
```

### PR 6：`runtime/durable-langgraph-hitl`

**修改：**

```text
pipeline/graph_checkpointer.py
graphs/reproduce_graph.py
graphs/productize_graph.py
pipeline/graph_hitl_runner.py
```

**验收：**

- 服务重启后 waiting approval 仍存在；
- 用户编辑的 plan revision 出现在 checkpoint state；
- reject command 后 runner 零调用；
- approve 后从原节点继续，而不是重新跑整条 pipeline。

## O.3 第三批 PR：前端工作台

### PR 7：`frontend/split-workspace-shell`

将当前 `WorkspaceShell` 拆成：

```text
Workbench
ProjectSidebar
Conversation
Composer
InspectorPanel
ApprovalPart
RunConnectionIndicator
```

第一步不必立刻改视觉，先把网络副作用迁到 hooks 和 stores。单个组件建议不超过 250–350 行。

### PR 8：`frontend/chat-message-parts`

把 timeline event 转成：

```text
TextPart
ToolPart
ArtifactPart
PlanReviewPart
ErrorPart
```

审批进入对话主流；右侧只保留详情与预览。

### PR 9：`frontend/linear-visual-system`

建立统一 token：

```css
/* frontend/app/globals.css */
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;
  --muted: 240 4.8% 95.9%;
  --muted-foreground: 240 3.8% 46.1%;
  --border: 240 5.9% 90%;
  --ring: 240 5% 64.9%;
  --radius: 0.75rem;
}

.dark {
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  --muted: 240 3.7% 15.9%;
  --muted-foreground: 240 5% 64.9%;
  --border: 240 3.7% 15.9%;
  --ring: 240 4.9% 83.9%;
}
```

动画原则：

```css
.interactive {
  transition:
    background-color 140ms ease,
    border-color 140ms ease,
    opacity 140ms ease,
    transform 140ms ease;
}

.interactive:active {
  transform: scale(0.985);
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

不要使用大面积玻璃拟态、强渐变和无意义持续动画。高级感主要来自信息层级、间距、排版、真实反馈和稳定过渡。

## O.4 第四批 PR：真实 Productize

### PR 10：`productize/nextjs-app-contract`

停止把 static bundle 作为成功结果。保留旧生成器只作为：

```text
productize/legacy_static_mock/
```

新链路必须生成 Next.js App Router 项目并有 `npm run build`。

### PR 11：`productize/build-test-repair-loop`

新增 typed verifier、最多 3 轮 patch repair、日志 artifact、失败可解释报告。

### PR 12：`preview/isolated-live-preview`

容器启动、代理、健康检查、HMR、停止和过期回收完整打通。前端 Preview 只读取真实 `preview.created` Artifact/Event。

---

# P. 改造完成后的 Definition of Done

PaperPilot 只有同时满足以下条件，才算从“展示型原型”升级为真正可用的论文产品化工作台：

1. 页面刷新、后端重启和短暂断网后，Run 可以恢复且不会伪造状态；
2. 模型输出以 token/delta 实时显示，不需要刷新会话；
3. Plan 编辑会真实改变 Graph 后续执行步骤；
4. Command/Patch 审批会真实阻断或恢复执行；
5. API Key 不会从后端返回、不进入 Run JSON、不明文写入仓库；
6. 所有仓库代码和生成代码只在容器隔离环境安装与执行；
7. Productize 结果至少能通过真实 `npm ci + npm run build + unit test + Playwright`；
8. Preview 来自真实运行容器，不是固定 iframe 或静态状态文案；
9. Graph 节点状态来自结构化事件，不通过 message 关键词推断；
10. Reproduce Contract 由仓库证据和论文证据动态生成，不固定要求 `main.py`；
11. 前端不存在一个承担全部业务的 1000+ 行 God Component；
12. 每个失败都能定位到 stage、issue category、文件和日志 Artifact；
13. Mock fallback 必须明确标注，不能被 UI 表述成真实模型结果；
14. 核心链路有刷新、重连、重启、审批、取消、构建失败和修复的 E2E 测试。

---

# Q. 本轮复核后的最终优先级

```text
P0-1  API Key 改为 Secret Store
P0-2  Host subprocess 改为容器执行
P0-3  Run/Event/Checkpoint 持久化
P0-4  Sequence SSE + 前端 reducer，修复实时输出
P0-5  Plan/Action 改成真正 LangGraph interrupt/resume

P1-1  拆分 WorkspaceShell
P1-2  Message Parts + 对话内审批
P1-3  取消关键词 Graph 状态推断
P1-4  Reproduce 动态 RepositoryIndex/Contract

P1-5  Productize Next.js App Contract
P1-6  Build-Test-Repair + Playwright
P1-7  Docker Preview + Proxy + HMR

P2-1  多 Project/Thread/Branch
P2-2  Artifact versioning 和 Diff
P2-3  Token/成本/耗时可观测性
P2-4  多用户鉴权、配额与审计日志
```

最关键的判断仍然是：**不要继续把时间主要投入到旧页面的局部美化。先让状态、执行、审批、构建和预览变成真的，再用 ChatGPT/Codex/Claude 风格的信息架构包住这些真实能力。** 否则 UI 越精致，用户越容易发现后端状态与实际结果不一致。


---

# 18. 代码增强版：基于当前仓库文件的直接改造实现

> 本章不是伪代码清单，而是按照当前仓库中的 `workspace-shell.tsx`、`api.ts`、`run_service.py`、`graph_service.py`、`event_service.py`、`runs.py`、`reproduce_graph.py` 和 `productize_graph.py` 给出的落地拆分方案。建议先新建文件，再逐步迁移旧代码，避免一次性重写导致现有功能全部失效。

## 18.1 当前巨型文件应如何拆

当前关键文件规模：

```text
frontend/components/workspace-shell.tsx   ≈ 1303 lines
frontend/lib/api.ts                       ≈ 560 lines
backend/services/run_service.py           ≈ 2092 lines
backend/services/graph_service.py         ≈ 391 lines
backend/services/event_service.py         ≈ 89 lines
```

建议拆成：

```text
frontend/
├── app/
│   └── workspace/[threadId]/page.tsx
├── features/
│   ├── threads/
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   └── thread-sidebar.tsx
│   ├── runs/
│   │   ├── api.ts
│   │   ├── event-reducer.ts
│   │   ├── run-provider.tsx
│   │   ├── run-timeline.tsx
│   │   └── use-run-events.ts
│   ├── chat/
│   │   ├── message-list.tsx
│   │   ├── message-item.tsx
│   │   ├── tool-call-card.tsx
│   │   └── composer.tsx
│   ├── artifacts/
│   │   ├── artifact-panel.tsx
│   │   ├── code-editor.tsx
│   │   └── diff-viewer.tsx
│   ├── preview/
│   │   ├── preview-frame.tsx
│   │   ├── preview-toolbar.tsx
│   │   └── use-preview-status.ts
│   └── approvals/
│       ├── approval-card.tsx
│       └── approval-dialog.tsx
├── lib/
│   ├── api-client.ts
│   ├── query-client.ts
│   └── schemas.ts
└── stores/
    └── ui-store.ts

backend/
├── api/
│   ├── threads.py
│   ├── messages.py
│   ├── runs.py
│   ├── approvals.py
│   ├── events.py
│   └── preview.py
├── domain/
│   ├── models.py
│   ├── events.py
│   └── enums.py
├── repositories/
│   ├── run_repository.py
│   ├── event_repository.py
│   ├── message_repository.py
│   └── artifact_repository.py
├── runtime/
│   ├── run_manager.py
│   ├── graph_executor.py
│   ├── event_publisher.py
│   ├── docker_runner.py
│   └── preview_manager.py
└── services/
    ├── run_application_service.py
    ├── approval_service.py
    └── artifact_service.py
```

原则是：

- React 组件不直接维护后端实体的多个副本；
- `run_service.py` 不再同时负责文件、Agent、事件、快照、线程和业务映射；
- Event Store 是运行状态的事实来源；
- Zustand 只保存 UI 偏好，不保存 Run 真值；
- 后端状态由数据库和 LangGraph checkpoint 恢复。

---

## 18.2 统一事件协议

当前事件服务只需要负责广播，但必须先统一事件类型。否则前端仍会用字符串内容推断阶段。

### 新建 `backend/domain/events.py`

```python
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class RunEventType(StrEnum):
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    RUN_STATUS_CHANGED = "run.status_changed"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"

    NODE_STARTED = "node.started"
    NODE_PROGRESS = "node.progress"
    NODE_COMPLETED = "node.completed"
    NODE_FAILED = "node.failed"

    MESSAGE_CREATED = "message.created"
    MESSAGE_DELTA = "message.delta"
    MESSAGE_COMPLETED = "message.completed"

    TOOL_STARTED = "tool.started"
    TOOL_OUTPUT = "tool.output"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    APPROVAL_REQUIRED = "approval.required"
    APPROVAL_RESOLVED = "approval.resolved"

    ARTIFACT_CREATED = "artifact.created"
    ARTIFACT_UPDATED = "artifact.updated"

    PREVIEW_STARTING = "preview.starting"
    PREVIEW_READY = "preview.ready"
    PREVIEW_FAILED = "preview.failed"
    PREVIEW_STOPPED = "preview.stopped"


class RunEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    sequence: int
    type: RunEventType
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    node_id: str | None = None
    message_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: Literal[1] = 1
```

事件必须带单调递增的 `sequence`。前端重连时传 `after=<lastSequence>`，避免刷新后漏事件或者重复追加。

### 新建 `backend/repositories/event_repository.py`

```python
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock

from backend.domain.events import RunEvent


class EventRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_events (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    node_id TEXT,
                    message_id TEXT,
                    payload_json TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    UNIQUE(run_id, sequence)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_run_events_run_seq "
                "ON run_events(run_id, sequence)"
            )

    def next_sequence(self, run_id: str) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS value "
                "FROM run_events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return int(row["value"]) + 1

    def append(self, event: RunEvent) -> RunEvent:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO run_events (
                    id, run_id, sequence, type, created_at,
                    node_id, message_id, payload_json, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.run_id,
                    event.sequence,
                    event.type.value,
                    event.created_at.isoformat(),
                    event.node_id,
                    event.message_id,
                    json.dumps(event.payload, ensure_ascii=False),
                    event.schema_version,
                ),
            )
        return event

    def list_after(
        self,
        *,
        run_id: str,
        after: int = 0,
        limit: int = 500,
    ) -> list[RunEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM run_events
                WHERE run_id = ? AND sequence > ?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (run_id, after, limit),
            ).fetchall()

        return [
            RunEvent.model_validate(
                {
                    "id": row["id"],
                    "run_id": row["run_id"],
                    "sequence": row["sequence"],
                    "type": row["type"],
                    "created_at": row["created_at"],
                    "node_id": row["node_id"],
                    "message_id": row["message_id"],
                    "payload": json.loads(row["payload_json"]),
                    "schema_version": row["schema_version"],
                }
            )
            for row in rows
        ]
```

---

## 18.3 把当前内存事件服务升级为“持久化 + 广播”

### 替换 `backend/services/event_service.py`

```python
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

from backend.domain.events import RunEvent, RunEventType
from backend.repositories.event_repository import EventRepository


class EventPublisher:
    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository
        self._subscribers: dict[str, set[asyncio.Queue[RunEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(
        self,
        *,
        run_id: str,
        event_type: RunEventType,
        payload: dict[str, Any] | None = None,
        node_id: str | None = None,
        message_id: str | None = None,
    ) -> RunEvent:
        event = RunEvent(
            run_id=run_id,
            sequence=self._repository.next_sequence(run_id),
            type=event_type,
            payload=payload or {},
            node_id=node_id,
            message_id=message_id,
        )
        self._repository.append(event)

        async with self._lock:
            queues = list(self._subscribers.get(run_id, set()))

        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # 慢客户端不能拖垮 Agent 执行。
                # 客户端重连后可从 Event Store 补齐。
                pass
        return event

    async def subscribe(
        self,
        *,
        run_id: str,
        after: int = 0,
    ) -> AsyncIterator[RunEvent]:
        # 先重放历史，再监听实时事件。
        for event in self._repository.list_after(run_id=run_id, after=after):
            yield event
            after = event.sequence

        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers[run_id].add(queue)

        try:
            while True:
                event = await queue.get()
                if event.sequence > after:
                    after = event.sequence
                    yield event
        finally:
            async with self._lock:
                self._subscribers[run_id].discard(queue)
```

相比当前纯内存广播，改造后：

- 页面刷新不会丢历史；
- 断线可续传；
- 多前端连接看到同一顺序；
- Run 完成后仍可查看完整 Trace；
- UI 不必通过轮询快照猜测中间过程。

---

## 18.4 使用 SSE 替代前端复杂 WebSocket 生命周期

PaperPilot 主要是服务端单向推送，审批和发送消息继续走 HTTP。因此 SSE 比 WebSocket 更简单，也更容易自动重连。

### 新建 `backend/api/events.py`

```python
import asyncio
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from backend.services.event_service import EventPublisher
from backend.dependencies import get_event_publisher

router = APIRouter(prefix="/api/runs", tags=["events"])


@router.get("/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    after: int = Query(default=0, ge=0),
    publisher: EventPublisher = Depends(get_event_publisher),
) -> StreamingResponse:
    async def event_stream():
        iterator = publisher.subscribe(run_id=run_id, after=after)
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(iterator.__anext__(), timeout=15)
                data = event.model_dump_json()
                yield (
                    f"id: {event.sequence}\n"
                    f"event: {event.type.value}\n"
                    f"data: {data}\n\n"
                )
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
            except StopAsyncIteration:
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

注意：Nginx 必须关闭该路由的 proxy buffering。

```nginx
location /api/runs/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
}
```

---

## 18.5 前端事件 reducer：彻底删除关键词状态推断

### 新建 `frontend/features/runs/event-reducer.ts`

```typescript
export type RunStatus =
  | "queued"
  | "running"
  | "waiting_approval"
  | "completed"
  | "failed"
  | "cancelled";

export type NodeStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "waiting_approval";

export interface StreamMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  status: "streaming" | "completed" | "failed";
}

export interface RunViewState {
  status: RunStatus;
  lastSequence: number;
  nodes: Record<string, NodeStatus>;
  messages: Record<string, StreamMessage>;
  messageOrder: string[];
  approvals: Record<string, unknown>;
  artifacts: Record<string, unknown>;
  preview: {
    status: "idle" | "starting" | "ready" | "failed";
    url?: string;
    error?: string;
  };
}

export interface RunEvent {
  id: string;
  run_id: string;
  sequence: number;
  type: string;
  node_id?: string | null;
  message_id?: string | null;
  payload: Record<string, any>;
}

export const initialRunState: RunViewState = {
  status: "queued",
  lastSequence: 0,
  nodes: {},
  messages: {},
  messageOrder: [],
  approvals: {},
  artifacts: {},
  preview: { status: "idle" },
};

export function reduceRunEvent(
  state: RunViewState,
  event: RunEvent,
): RunViewState {
  if (event.sequence <= state.lastSequence) return state;

  const next: RunViewState = {
    ...state,
    lastSequence: event.sequence,
    nodes: { ...state.nodes },
    messages: { ...state.messages },
    approvals: { ...state.approvals },
    artifacts: { ...state.artifacts },
    preview: { ...state.preview },
  };

  switch (event.type) {
    case "run.started":
      next.status = "running";
      break;
    case "run.status_changed":
      next.status = event.payload.status;
      break;
    case "run.completed":
      next.status = "completed";
      break;
    case "run.failed":
      next.status = "failed";
      break;
    case "run.cancelled":
      next.status = "cancelled";
      break;

    case "node.started":
      if (event.node_id) next.nodes[event.node_id] = "running";
      break;
    case "node.completed":
      if (event.node_id) next.nodes[event.node_id] = "completed";
      break;
    case "node.failed":
      if (event.node_id) next.nodes[event.node_id] = "failed";
      break;

    case "message.created": {
      const id = event.message_id!;
      next.messages[id] = {
        id,
        role: event.payload.role ?? "assistant",
        content: event.payload.content ?? "",
        status: "streaming",
      };
      if (!next.messageOrder.includes(id)) {
        next.messageOrder = [...next.messageOrder, id];
      }
      break;
    }
    case "message.delta": {
      const id = event.message_id!;
      const current = next.messages[id];
      if (current) {
        next.messages[id] = {
          ...current,
          content: current.content + String(event.payload.delta ?? ""),
        };
      }
      break;
    }
    case "message.completed": {
      const id = event.message_id!;
      const current = next.messages[id];
      if (current) next.messages[id] = { ...current, status: "completed" };
      break;
    }

    case "approval.required":
      next.status = "waiting_approval";
      next.approvals[event.payload.approval_id] = event.payload;
      if (event.node_id) next.nodes[event.node_id] = "waiting_approval";
      break;
    case "approval.resolved":
      delete next.approvals[event.payload.approval_id];
      next.status = "running";
      break;

    case "artifact.created":
    case "artifact.updated":
      next.artifacts[event.payload.artifact_id] = event.payload;
      break;

    case "preview.starting":
      next.preview = { status: "starting" };
      break;
    case "preview.ready":
      next.preview = { status: "ready", url: event.payload.url };
      break;
    case "preview.failed":
      next.preview = {
        status: "failed",
        error: event.payload.error ?? "Preview failed",
      };
      break;
  }

  return next;
}
```

这个 reducer 是前端唯一的运行状态转换入口。`WorkflowGraph`、时间线、聊天区和右侧预览都读取同一个 `RunViewState`。

---

## 18.6 前端 SSE Hook

### 新建 `frontend/features/runs/use-run-events.ts`

```typescript
"use client";

import { useEffect, useReducer, useRef } from "react";
import {
  initialRunState,
  reduceRunEvent,
  type RunEvent,
  type RunViewState,
} from "./event-reducer";

const API_BASE =
  process.env.NEXT_PUBLIC_PAPERPILOT_API_BASE ?? "http://127.0.0.1:8000";

export function useRunEvents(
  runId: string | null,
  initialState?: RunViewState,
) {
  const [state, dispatch] = useReducer(
    reduceRunEvent,
    initialState ?? initialRunState,
  );
  const lastSequenceRef = useRef(state.lastSequence);

  useEffect(() => {
    lastSequenceRef.current = state.lastSequence;
  }, [state.lastSequence]);

  useEffect(() => {
    if (!runId) return;

    let source: EventSource | null = null;
    let closed = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (closed) return;
      const after = lastSequenceRef.current;
      source = new EventSource(
        `${API_BASE}/api/runs/${runId}/events?after=${after}`,
        { withCredentials: true },
      );

      source.onmessage = (message) => {
        const event = JSON.parse(message.data) as RunEvent;
        dispatch(event);
      };

      // EventSource 对自定义 event 不会触发 onmessage，
      // 因此后端也可以不设置 event:；或者在此注册所有事件名。
      const eventNames = [
        "run.created", "run.started", "run.status_changed",
        "run.completed", "run.failed", "run.cancelled",
        "node.started", "node.progress", "node.completed", "node.failed",
        "message.created", "message.delta", "message.completed",
        "tool.started", "tool.output", "tool.completed", "tool.failed",
        "approval.required", "approval.resolved",
        "artifact.created", "artifact.updated",
        "preview.starting", "preview.ready", "preview.failed",
      ];

      for (const name of eventNames) {
        source.addEventListener(name, (message) => {
          dispatch(JSON.parse((message as MessageEvent).data) as RunEvent);
        });
      }

      source.onerror = () => {
        source?.close();
        retryTimer = setTimeout(connect, 1500);
      };
    };

    connect();
    return () => {
      closed = true;
      source?.close();
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [runId]);

  return state;
}
```

不要在该 Hook 中并行启动快照轮询，否则旧快照可能覆盖新事件。首次进入页面时只获取一次 Snapshot，之后完全由事件更新。

---

## 18.7 API Client 分模块，删除静默 Mock Fallback

当前 `frontend/lib/api.ts` 过大，且开发 fallback 容易让用户误以为真实后端已工作。建议统一请求层后按领域拆分。

### `frontend/lib/api-client.ts`

```typescript
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: unknown,
    message: string,
  ) {
    super(message);
  }
}

const API_BASE =
  process.env.NEXT_PUBLIC_PAPERPILOT_API_BASE ?? "http://127.0.0.1:8000";

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });

  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError(
      response.status,
      body,
      typeof body === "object" && body && "detail" in body
        ? String((body as any).detail)
        : `Request failed: ${response.status}`,
    );
  }
  return body as T;
}
```

### `frontend/features/runs/api.ts`

```typescript
import { apiRequest } from "@/lib/api-client";

export interface CreateRunInput {
  threadId: string;
  mode: "reproduce" | "productize";
  message: string;
  attachmentIds: string[];
  githubUrl?: string;
}

export async function createRun(input: CreateRunInput) {
  return apiRequest<{ run_id: string; status: string }>("/api/runs", {
    method: "POST",
    body: JSON.stringify({
      thread_id: input.threadId,
      mode: input.mode,
      message: input.message,
      attachment_ids: input.attachmentIds,
      github_url: input.githubUrl,
    }),
  });
}

export async function getRunSnapshot(runId: string) {
  return apiRequest(`/api/runs/${runId}`);
}

export async function cancelRun(runId: string) {
  return apiRequest(`/api/runs/${runId}/cancel`, { method: "POST" });
}

export async function resolveApproval(
  runId: string,
  approvalId: string,
  decision: "approve" | "reject",
  edits?: Record<string, unknown>,
) {
  return apiRequest(`/api/runs/${runId}/approvals/${approvalId}`, {
    method: "POST",
    body: JSON.stringify({ decision, edits }),
  });
}
```

Mock 数据只能由显式环境变量开启：

```typescript
export const MOCK_MODE = process.env.NEXT_PUBLIC_MOCK_MODE === "true";
```

生产构建中如果该变量为 true，CI 应直接失败。

---

## 18.8 `WorkspaceShell` 重构后的入口

### 新建 `frontend/features/workbench/workbench-page.tsx`

```tsx
"use client";

import { useState } from "react";
import { ThreadSidebar } from "@/features/threads/thread-sidebar";
import { MessageList } from "@/features/chat/message-list";
import { Composer } from "@/features/chat/composer";
import { RunTimeline } from "@/features/runs/run-timeline";
import { ArtifactPanel } from "@/features/artifacts/artifact-panel";
import { useRunEvents } from "@/features/runs/use-run-events";

interface Props {
  threadId: string;
  initialRunId?: string | null;
}

export function WorkbenchPage({ threadId, initialRunId = null }: Props) {
  const [runId, setRunId] = useState(initialRunId);
  const run = useRunEvents(runId);

  return (
    <div className="grid h-dvh grid-cols-[260px_minmax(0,1fr)_420px] bg-background">
      <ThreadSidebar activeThreadId={threadId} />

      <main className="flex min-w-0 flex-col border-x">
        <header className="flex h-12 items-center justify-between border-b px-4">
          <div className="min-w-0">
            <h1 className="truncate text-sm font-medium">PaperPilot</h1>
            <p className="text-xs text-muted-foreground">
              {run.status === "running" ? "Agent is working" : run.status}
            </p>
          </div>
          <RunTimeline state={run} />
        </header>

        <MessageList
          messages={run.messageOrder.map((id) => run.messages[id])}
          nodes={run.nodes}
          approvals={run.approvals}
          runId={runId}
        />

        <Composer
          threadId={threadId}
          activeRunId={runId}
          running={run.status === "running"}
          onRunCreated={setRunId}
        />
      </main>

      <ArtifactPanel
        runId={runId}
        artifacts={run.artifacts}
        preview={run.preview}
      />
    </div>
  );
}
```

这样入口组件只负责组合布局，不再包含上传、事件解析、审批请求、文件加载、流程推断、WebSocket 重连和预览逻辑。

---

## 18.9 真正的模型 Token Streaming

当前图节点通常在 LLM 调用完成后才返回结构化结果。要实现 ChatGPT／Claude 类实时输出，应让 LLM Client 支持 token callback，并将 delta 写入事件流。

### 修改 `tools/llm_client.py`

```python
from collections.abc import AsyncIterator
from openai import AsyncOpenAI


class LLMClient:
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def stream_text(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
```

### 新建 Agent 输出辅助器

```python
from uuid import uuid4

from backend.domain.events import RunEventType


async def stream_agent_text(
    *,
    run_id: str,
    node_id: str,
    llm,
    publisher,
    messages: list[dict[str, str]],
) -> str:
    message_id = str(uuid4())
    await publisher.publish(
        run_id=run_id,
        event_type=RunEventType.MESSAGE_CREATED,
        node_id=node_id,
        message_id=message_id,
        payload={"role": "assistant", "content": ""},
    )

    chunks: list[str] = []
    async for delta in llm.stream_text(messages=messages):
        chunks.append(delta)
        await publisher.publish(
            run_id=run_id,
            event_type=RunEventType.MESSAGE_DELTA,
            node_id=node_id,
            message_id=message_id,
            payload={"delta": delta},
        )

    text = "".join(chunks)
    await publisher.publish(
        run_id=run_id,
        event_type=RunEventType.MESSAGE_COMPLETED,
        node_id=node_id,
        message_id=message_id,
        payload={"content_length": len(text)},
    )
    return text
```

结构化输出场景可采用“两阶段输出”：

1. 流式输出自然语言进度和解释；
2. 再调用 structured output 得到可靠 JSON；
3. JSON 作为 Artifact，而不是把半截 JSON 直接流给 UI。

---

## 18.10 从 LangGraph 节点发出真实节点事件

当前 `graph_trace` 只是状态字段，前端不能精确知道节点开始时间。建议在执行器层包裹节点，而不是每个节点手写事件。

### 新建 `backend/runtime/node_instrumentation.py`

```python
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from backend.domain.events import RunEventType


def instrument_node(
    node_id: str,
    handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    publisher,
):
    async def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        run_id = str(state["run_id"])
        started = time.perf_counter()
        await publisher.publish(
            run_id=run_id,
            event_type=RunEventType.NODE_STARTED,
            node_id=node_id,
            payload={},
        )
        try:
            result = await handler(state)
        except Exception as exc:
            await publisher.publish(
                run_id=run_id,
                event_type=RunEventType.NODE_FAILED,
                node_id=node_id,
                payload={
                    "error": str(exc),
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                },
            )
            raise

        await publisher.publish(
            run_id=run_id,
            event_type=RunEventType.NODE_COMPLETED,
            node_id=node_id,
            payload={
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "output_keys": sorted(result.keys()),
            },
        )
        return result

    return wrapped
```

如果暂时保留同步节点，可用 `anyio.to_thread.run_sync` 包裹，避免同步 LLM/文件调用阻塞 FastAPI event loop。

---

## 18.11 真正可恢复的 LangGraph Checkpoint

当前 graph 构建函数已经接受 `checkpointer` 和 `interrupt_after`，这是可以直接利用的。关键是不要每次启动 Run 都重新从 START 执行。

### 初始化 SQLite Checkpointer

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


async def create_checkpointer(db_path: str):
    saver = AsyncSqliteSaver.from_conn_string(db_path)
    await saver.setup()
    return saver
```

### 执行 Run

```python
async def execute_graph_run(
    *,
    graph,
    run_id: str,
    initial_state: dict,
    publisher,
) -> dict:
    config = {
        "configurable": {
            "thread_id": run_id,
            "checkpoint_ns": "paperpilot",
        }
    }

    await publisher.publish(
        run_id=run_id,
        event_type=RunEventType.RUN_STARTED,
        payload={},
    )

    try:
        result = await graph.ainvoke(initial_state, config=config)
    except asyncio.CancelledError:
        await publisher.publish(
            run_id=run_id,
            event_type=RunEventType.RUN_CANCELLED,
        )
        raise
    except Exception as exc:
        await publisher.publish(
            run_id=run_id,
            event_type=RunEventType.RUN_FAILED,
            payload={"error": str(exc)},
        )
        raise

    await publisher.publish(
        run_id=run_id,
        event_type=RunEventType.RUN_COMPLETED,
        payload={"result_keys": sorted(result.keys())},
    )
    return result
```

### 审批后恢复

```python
from langgraph.types import Command


async def resume_after_approval(
    *,
    graph,
    run_id: str,
    approval_payload: dict,
):
    config = {
        "configurable": {
            "thread_id": run_id,
            "checkpoint_ns": "paperpilot",
        }
    }
    return await graph.ainvoke(
        Command(resume=approval_payload),
        config=config,
    )
```

不要只把审批结果写入前端或 `pending_action` JSON；必须通过 `Command(resume=...)` 恢复同一个 checkpoint。

---

## 18.12 把 Reproduce 的命令审核改成真正 interrupt

当前 `reproduce_graph.py` 会生成 `pending_human_review`，但路线仍继续进入 summary 和 implementation。建议风险命令需要审批时直接中断。

### 修改节点逻辑

```python
from langgraph.types import interrupt


def command_risk_router(state: ReproduceState) -> dict[str, Any]:
    classified = classify_command_plans(list(state.get("command_plans") or []))
    route = route_command_plans(classified)
    cwd = str(state.get("repo_path") or "")

    if route == "review":
        decision = interrupt(
            {
                "kind": "command_approval",
                "title": "Review generated commands",
                "commands": classified,
                "cwd": cwd,
                "allow_edit": True,
            }
        )
        if decision.get("decision") != "approve":
            return {
                "command_plans": classified,
                "command_route": "blocked",
                "command_results": summarize_unexecuted_commands(
                    classified, "rejected"
                ),
                "graph_trace": ["command_risk_router"],
            }
        classified = decision.get("edited_commands", classified)
        route = "safe"

    return {
        "command_plans": classified,
        "command_route": route,
        "graph_trace": ["command_risk_router"],
    }
```

这样用户修改命令后，后端执行的是修改后的命令，不再出现“界面编辑了计划但 Agent 没使用”的假交互。

---

## 18.13 Productize 不能再止于静态 Scaffold

当前 `productize_graph.py` 的执行链是：

```text
build_prototype -> product_contract -> evaluate -> revise
-> scaffold_product -> inspect_product -> final_evaluation
```

建议扩成真实工程闭环：

```text
plan
-> generate_project
-> install_dependencies
-> typecheck
-> build
-> start_preview
-> browser_smoke_test
-> evaluate_ui
-> repair
-> final_verify
```

### 新建状态字段

```python
class ProductBuildState(TypedDict, total=False):
    project_dir: str
    package_manager: str
    install_result: dict
    typecheck_result: dict
    build_result: dict
    preview_id: str
    preview_url: str
    browser_report: dict
    repair_count: int
    max_repairs: int
```

### 核心节点

```python
async def install_dependencies(state: ProductizeState) -> dict:
    result = await sandbox.run(
        workspace=Path(state["project_dir"]),
        command=["npm", "ci", "--ignore-scripts"],
        network_policy="npm-registry-only",
        timeout_s=300,
    )
    return {"install_result": result}


async def typecheck_project(state: ProductizeState) -> dict:
    result = await sandbox.run(
        workspace=Path(state["project_dir"]),
        command=["npm", "run", "typecheck"],
        network_policy="none",
        timeout_s=180,
    )
    return {"typecheck_result": result}


async def build_project(state: ProductizeState) -> dict:
    result = await sandbox.run(
        workspace=Path(state["project_dir"]),
        command=["npm", "run", "build"],
        network_policy="none",
        timeout_s=300,
    )
    return {"build_result": result}


def route_after_build(state: ProductizeState) -> str:
    if state["build_result"].get("exit_code") == 0:
        return "start_preview"
    if int(state.get("repair_count", 0)) < int(state.get("max_repairs", 2)):
        return "repair_project"
    return "finish_with_warnings"
```

### 图连接

```python
builder.add_node("generate_project", generate_project)
builder.add_node("install_dependencies", install_dependencies)
builder.add_node("typecheck_project", typecheck_project)
builder.add_node("build_project", build_project)
builder.add_node("repair_project", repair_project)
builder.add_node("start_preview", start_preview)
builder.add_node("browser_smoke_test", browser_smoke_test)

builder.add_edge("product_contract", "generate_project")
builder.add_edge("generate_project", "install_dependencies")
builder.add_edge("install_dependencies", "typecheck_project")
builder.add_edge("typecheck_project", "build_project")
builder.add_conditional_edges(
    "build_project",
    route_after_build,
    {
        "start_preview": "start_preview",
        "repair_project": "repair_project",
        "finish_with_warnings": "finish_with_warnings",
    },
)
builder.add_edge("repair_project", "typecheck_project")
builder.add_edge("start_preview", "browser_smoke_test")
```

---

## 18.14 Docker Sandbox 完整版本

### `backend/runtime/docker_runner.py`

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import docker
from docker.errors import ContainerError, ImageNotFound


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class DockerRunner:
    def __init__(self) -> None:
        self.client = docker.from_env()

    async def run(
        self,
        *,
        workspace: Path,
        command: list[str],
        image: str = "paperpilot/runner:py312-node20",
        timeout_s: int = 300,
        network_policy: str = "none",
    ) -> CommandResult:
        return await asyncio.to_thread(
            self._run_sync,
            workspace.resolve(strict=True),
            command,
            image,
            timeout_s,
            network_policy,
        )

    def _run_sync(
        self,
        workspace: Path,
        command: list[str],
        image: str,
        timeout_s: int,
        network_policy: str,
    ) -> CommandResult:
        network_mode = "none" if network_policy == "none" else "bridge"
        container = self.client.containers.create(
            image=image,
            command=command,
            working_dir="/workspace",
            user="1000:1000",
            network_mode=network_mode,
            volumes={
                str(workspace): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
            environment={
                "HOME": "/tmp/home",
                "CI": "1",
                "NO_COLOR": "1",
            },
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            read_only=True,
            tmpfs={
                "/tmp": "rw,noexec,nosuid,size=512m",
                "/tmp/home": "rw,noexec,nosuid,size=64m",
            },
            mem_limit="2g",
            nano_cpus=2_000_000_000,
            pids_limit=256,
            detach=True,
            stdout=True,
            stderr=True,
        )

        try:
            container.start()
            try:
                result = container.wait(timeout=timeout_s)
            except Exception:
                container.kill()
                logs = container.logs(stdout=True, stderr=True).decode(
                    "utf-8", errors="replace"
                )
                return CommandResult(
                    exit_code=124,
                    stdout=logs,
                    stderr="Command timed out",
                    timed_out=True,
                )

            stdout = container.logs(stdout=True, stderr=False).decode(
                "utf-8", errors="replace"
            )
            stderr = container.logs(stdout=False, stderr=True).decode(
                "utf-8", errors="replace"
            )
            return CommandResult(
                exit_code=int(result.get("StatusCode", 1)),
                stdout=stdout[-200_000:],
                stderr=stderr[-200_000:],
            )
        finally:
            container.remove(force=True)
```

生产中还应增加：镜像白名单、命令参数校验、出网代理白名单、磁盘配额、容器审计日志和定期清理。

---

## 18.15 Preview Manager 和反向代理

### `backend/runtime/preview_manager.py`

```python
from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import docker


@dataclass
class PreviewInstance:
    id: str
    run_id: str
    container_id: str
    host_port: int
    status: str


class PreviewManager:
    def __init__(self) -> None:
        self.client = docker.from_env()
        self.instances: dict[str, PreviewInstance] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _free_port() -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    async def start(self, *, run_id: str, project_dir: Path) -> PreviewInstance:
        async with self._lock:
            preview_id = str(uuid4())
            host_port = self._free_port()
            container = await asyncio.to_thread(
                self.client.containers.run,
                "node:20-alpine",
                ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"],
                working_dir="/workspace",
                volumes={
                    str(project_dir.resolve()): {
                        "bind": "/workspace",
                        "mode": "rw",
                    }
                },
                ports={"3000/tcp": ("127.0.0.1", host_port)},
                user="1000:1000",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                mem_limit="1g",
                pids_limit=256,
                detach=True,
                remove=False,
            )
            instance = PreviewInstance(
                id=preview_id,
                run_id=run_id,
                container_id=container.id,
                host_port=host_port,
                status="starting",
            )
            self.instances[preview_id] = instance
            return instance

    async def stop(self, preview_id: str) -> None:
        instance = self.instances.pop(preview_id, None)
        if not instance:
            return
        container = self.client.containers.get(instance.container_id)
        await asyncio.to_thread(container.remove, force=True)
```

### Preview 代理路由

```python
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

router = APIRouter(prefix="/api/preview")


@router.api_route(
    "/{preview_id}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy_preview(preview_id: str, path: str, request: Request):
    instance = preview_manager.instances.get(preview_id)
    if not instance:
        raise HTTPException(404, "Preview not found")

    target = f"http://127.0.0.1:{instance.host_port}/{path}"
    body = await request.body()
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }

    async with httpx.AsyncClient(follow_redirects=False) as client:
        upstream = await client.request(
            request.method,
            target,
            params=request.query_params,
            content=body,
            headers=headers,
            timeout=30,
        )

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in {"content-length", "transfer-encoding", "connection"}
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
```

对于 Next.js HMR 的 WebSocket，建议由 Nginx/Traefik 做动态代理，或者预览环境先采用 `next build && next start`，避免应用层自行代理 WebSocket。

---

## 18.16 Preview Frame：显示真实状态而不是固定 Checklist

```tsx
interface PreviewFrameProps {
  status: "idle" | "starting" | "ready" | "failed";
  url?: string;
  error?: string;
}

export function PreviewFrame({ status, url, error }: PreviewFrameProps) {
  if (status === "idle") {
    return (
      <div className="grid h-full place-items-center text-sm text-muted-foreground">
        Preview will appear after the project builds.
      </div>
    );
  }

  if (status === "starting") {
    return (
      <div className="grid h-full place-items-center">
        <div className="space-y-3 text-center">
          <div className="mx-auto size-5 animate-spin rounded-full border-2 border-muted border-t-foreground" />
          <p className="text-sm">Starting preview server…</p>
        </div>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="m-4 rounded-lg border border-destructive/30 bg-destructive/5 p-4">
        <p className="text-sm font-medium">Preview failed</p>
        <pre className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground">
          {error}
        </pre>
      </div>
    );
  }

  return (
    <iframe
      title="PaperPilot live preview"
      src={url}
      className="h-full w-full bg-white"
      sandbox="allow-forms allow-modals allow-popups allow-scripts allow-same-origin"
    />
  );
}
```

后端没有发出 `preview.ready` 之前，前端不能自行显示“App generated ✓”或“Verified ✓”。

---

## 18.17 Run Repository：不要依赖进程内字典

### `backend/repositories/run_repository.py`

```python
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RunRecord:
    id: str
    thread_id: str
    mode: str
    status: str
    input_json: dict
    output_json: dict | None
    error: str | None
    created_at: str
    updated_at: str


class RunRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    output_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(self, record: RunRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.thread_id,
                    record.mode,
                    record.status,
                    json.dumps(record.input_json, ensure_ascii=False),
                    json.dumps(record.output_json, ensure_ascii=False)
                    if record.output_json is not None
                    else None,
                    record.error,
                    record.created_at,
                    record.updated_at,
                ),
            )

    def update_status(
        self,
        run_id: str,
        status: str,
        *,
        output: dict | None = None,
        error: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, output_json = COALESCE(?, output_json),
                    error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(output, ensure_ascii=False)
                    if output is not None
                    else None,
                    error,
                    datetime.now(timezone.utc).isoformat(),
                    run_id,
                ),
            )
```

后端重启时：

- `completed/failed/cancelled` 保持原状态；
- `waiting_approval` 从 checkpoint 恢复；
- `running` 标记为 `interrupted`，由恢复任务继续，而不是直接伪造失败；
- UI 重新进入页面后获取数据库 Snapshot 和历史事件。

---

## 18.18 Run Manager：分离业务调度和 HTTP Router

```python
from __future__ import annotations

import asyncio
from uuid import uuid4


class RunManager:
    def __init__(self, run_repo, graph_factory, publisher) -> None:
        self.run_repo = run_repo
        self.graph_factory = graph_factory
        self.publisher = publisher
        self.tasks: dict[str, asyncio.Task] = {}

    async def create_run(self, *, thread_id: str, mode: str, payload: dict) -> str:
        run_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.run_repo.create(
            RunRecord(
                id=run_id,
                thread_id=thread_id,
                mode=mode,
                status="queued",
                input_json=payload,
                output_json=None,
                error=None,
                created_at=now,
                updated_at=now,
            )
        )
        await self.publisher.publish(
            run_id=run_id,
            event_type=RunEventType.RUN_CREATED,
            payload={"mode": mode, "thread_id": thread_id},
        )
        self.tasks[run_id] = asyncio.create_task(
            self._execute(run_id=run_id, mode=mode, payload=payload)
        )
        return run_id

    async def _execute(self, *, run_id: str, mode: str, payload: dict) -> None:
        graph = self.graph_factory.create(mode)
        self.run_repo.update_status(run_id, "running")
        try:
            result = await execute_graph_run(
                graph=graph,
                run_id=run_id,
                initial_state={"run_id": run_id, **payload},
                publisher=self.publisher,
            )
        except asyncio.CancelledError:
            self.run_repo.update_status(run_id, "cancelled")
            raise
        except Exception as exc:
            self.run_repo.update_status(run_id, "failed", error=str(exc))
        else:
            self.run_repo.update_status(run_id, "completed", output=result)
        finally:
            self.tasks.pop(run_id, None)

    async def cancel(self, run_id: str) -> None:
        task = self.tasks.get(run_id)
        if task and not task.done():
            task.cancel()
```

注意：单机 `asyncio.create_task` 仍不是最终生产队列。后续可替换为 Dramatiq/Celery/Arq，但领域接口不用变。

---

## 18.19 Router 应保持很薄

### 重写 `backend/routers/runs.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    thread_id: str
    mode: Literal["reproduce", "productize"]
    message: str = Field(min_length=1, max_length=20_000)
    attachment_ids: list[str] = Field(default_factory=list)
    github_url: str | None = None


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    body: CreateRunRequest,
    manager: RunManager = Depends(get_run_manager),
):
    run_id = await manager.create_run(
        thread_id=body.thread_id,
        mode=body.mode,
        payload=body.model_dump(),
    )
    return {"run_id": run_id, "status": "queued"}


@router.get("/{run_id}")
def get_run(
    run_id: str,
    repository: RunRepository = Depends(get_run_repository),
):
    run = repository.get(run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run


@router.post("/{run_id}/cancel", status_code=202)
async def cancel_run(
    run_id: str,
    manager: RunManager = Depends(get_run_manager),
):
    await manager.cancel(run_id)
    return {"run_id": run_id, "status": "cancelling"}
```

Router 中不要再写文件复制、图状态映射、Artifact 生成和 Agent 调用。

---

## 18.20 聊天消息模型

PaperPilot 的主界面应从“运行控制面板”转向“对话驱动的工作台”。Thread、Message 和 Run 要分离：

```python
class Thread(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class Message(BaseModel):
    id: str
    thread_id: str
    run_id: str | None
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    status: Literal["streaming", "completed", "failed"]
    created_at: datetime
    metadata: dict = Field(default_factory=dict)
```

一次用户发送对应：

```text
Thread
  ├── User Message
  ├── Run
  ├── Assistant streaming Message
  ├── Tool Messages
  └── Final Assistant Message
```

Run 历史不等于对话历史。用户后续可以在同一 Thread 中基于之前 Artifact 继续修改产品。

---

## 18.21 Composer 的真实交互

```tsx
export function Composer({
  threadId,
  activeRunId,
  running,
  onRunCreated,
}: {
  threadId: string;
  activeRunId: string | null;
  running: boolean;
  onRunCreated: (runId: string) => void;
}) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"productize" | "reproduce">("productize");
  const [attachments, setAttachments] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    const value = text.trim();
    if (!value || submitting) return;
    setSubmitting(true);
    try {
      const result = await createRun({
        threadId,
        mode,
        message: value,
        attachmentIds: attachments,
      });
      setText("");
      setAttachments([]);
      onRunCreated(result.run_id);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="border-t bg-background p-3">
      <div className="rounded-2xl border bg-card shadow-sm focus-within:ring-1">
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
          placeholder="Ask PaperPilot to analyze, reproduce, or build…"
          className="min-h-20 w-full resize-none bg-transparent px-4 pt-3 text-sm outline-none"
        />
        <div className="flex items-center justify-between px-3 pb-3">
          <div className="flex items-center gap-2">
            <ModeSelector value={mode} onChange={setMode} />
            <AttachmentButton onUploaded={(id) => setAttachments((x) => [...x, id])} />
          </div>
          {running && activeRunId ? (
            <Button variant="secondary" onClick={() => cancelRun(activeRunId)}>
              Stop
            </Button>
          ) : (
            <Button disabled={!text.trim() || submitting} onClick={submit}>
              Send
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
```

这种交互比独立的“Start Run”表单更接近 ChatGPT、Claude 和 Codex。

---

## 18.22 审批卡片必须展示影响范围

```tsx
export function ApprovalCard({
  runId,
  approval,
}: {
  runId: string;
  approval: {
    approval_id: string;
    title: string;
    kind: string;
    commands?: Array<{ command: string; risk: string; reason: string }>;
    patch?: string;
  };
}) {
  const [editedCommands, setEditedCommands] = useState(approval.commands ?? []);
  const [loading, setLoading] = useState(false);

  async function decide(decision: "approve" | "reject") {
    setLoading(true);
    try {
      await resolveApproval(runId, approval.approval_id, decision, {
        edited_commands: editedCommands,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="my-3 overflow-hidden rounded-xl border bg-card">
      <div className="border-b px-4 py-3">
        <p className="text-sm font-medium">{approval.title}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          PaperPilot paused before executing a potentially impactful action.
        </p>
      </div>

      <div className="space-y-2 p-3">
        {editedCommands.map((item, index) => (
          <div key={index} className="rounded-lg bg-muted/50 p-3">
            <textarea
              value={item.command}
              onChange={(event) => {
                const next = [...editedCommands];
                next[index] = { ...item, command: event.target.value };
                setEditedCommands(next);
              }}
              className="w-full resize-y bg-transparent font-mono text-xs outline-none"
            />
            <p className="mt-2 text-xs text-muted-foreground">{item.reason}</p>
          </div>
        ))}
      </div>

      <div className="flex justify-end gap-2 border-t p-3">
        <Button variant="ghost" disabled={loading} onClick={() => decide("reject")}>
          Reject
        </Button>
        <Button disabled={loading} onClick={() => decide("approve")}>
          Approve and continue
        </Button>
      </div>
    </section>
  );
}
```

审批成功后不要前端自行把节点设为完成；等待后端发出 `approval.resolved` 和后续 `node.started`。

---

## 18.23 UI 视觉系统

建议采用黑白灰为主、低饱和状态色，减少目前“IDE 仪表盘”式高密度卡片。

### Tailwind Token

```css
@layer base {
  :root {
    --background: 0 0% 99%;
    --foreground: 240 6% 10%;
    --card: 0 0% 100%;
    --card-foreground: 240 6% 10%;
    --muted: 240 5% 96%;
    --muted-foreground: 240 4% 46%;
    --border: 240 6% 90%;
    --primary: 240 6% 10%;
    --primary-foreground: 0 0% 98%;
    --radius: 0.75rem;
  }

  .dark {
    --background: 240 7% 7%;
    --foreground: 0 0% 95%;
    --card: 240 6% 9%;
    --card-foreground: 0 0% 95%;
    --muted: 240 5% 13%;
    --muted-foreground: 240 5% 64%;
    --border: 240 5% 18%;
    --primary: 0 0% 95%;
    --primary-foreground: 240 7% 7%;
  }
}
```

### Motion 原则

```tsx
<motion.div
  initial={{ opacity: 0, y: 6 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
/>
```

只在以下位置使用动画：

- 新消息进入；
- Tool call 展开；
- Inspector 切换；
- Preview ready；
- Approval 出现。

不要让流程图节点持续闪烁或大幅移动。

---

## 18.24 构建与浏览器验证

### Playwright Smoke Test

```typescript
import { test, expect } from "@playwright/test";

const previewUrl = process.env.PREVIEW_URL!;

test("generated product loads and primary action works", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.goto(previewUrl, { waitUntil: "networkidle" });
  await expect(page.locator("body")).not.toBeEmpty();

  const primaryAction = page.getByTestId("primary-action");
  await expect(primaryAction).toBeVisible();
  await primaryAction.click();
  await expect(page.getByTestId("result-panel")).toBeVisible();

  expect(consoleErrors).toEqual([]);
});
```

Generator Prompt 中必须要求关键控件携带稳定的 `data-testid`，否则自动验证只能依赖脆弱文本。

---

## 18.25 Agent 代码生成质量的增强

不要让一个 Agent 一次性生成整个项目。推荐职责：

```text
PaperParser       -> evidence.json
CapabilityAgent   -> capability_card.json
ProductPlanner    -> product_spec.json + acceptance_tests.json
Architect         -> file_manifest.json + interfaces.json
CodeGenerator     -> per-file generation
TestWriter        -> tests
BuildVerifier     -> deterministic commands
RepairAgent       -> patch only
UIReviewer        -> screenshot + DOM report
```

### File Manifest Schema

```python
class PlannedFile(BaseModel):
    path: str
    purpose: str
    exports: list[str] = []
    dependencies: list[str] = []
    acceptance_criteria: list[str] = []


class ProjectManifest(BaseModel):
    framework: Literal["nextjs"]
    package_manager: Literal["npm"]
    files: list[PlannedFile]
    routes: list[str]
    commands: dict[str, str]
    environment_variables: list[str]
```

生成文件时给 Agent 的上下文只包含：

- product spec；
- manifest 当前文件条目；
- 相关接口；
- 已生成依赖文件摘要；
- 测试要求。

不要把整篇论文、所有历史消息和整个仓库同时塞给每次文件生成调用。

---

## 18.26 Patch-based Repair

Repair Agent 不应重新生成整个项目，只输出结构化 Patch：

```python
class FilePatch(BaseModel):
    path: str
    old_text: str
    new_text: str
    reason: str


class RepairBundle(BaseModel):
    diagnosis: str
    patches: list[FilePatch]
    expected_fixed_errors: list[str]
```

应用前检查：

```python
def apply_safe_patch(root: Path, patch: FilePatch) -> None:
    target = (root / patch.path).resolve()
    if root.resolve() not in target.parents:
        raise ValueError("Path traversal rejected")

    content = target.read_text(encoding="utf-8")
    count = content.count(patch.old_text)
    if count != 1:
        raise ValueError(
            f"Patch anchor must match exactly once, got {count}: {patch.path}"
        )
    target.write_text(
        content.replace(patch.old_text, patch.new_text, 1),
        encoding="utf-8",
    )
```

每次 Repair 后只重跑失败阶段及其下游，不必重新解析论文和重新规划产品。

---

## 18.27 数据库表建议

```sql
CREATE TABLE threads (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES threads(id),
  run_id TEXT,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  status TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES threads(id),
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  input_json TEXT NOT NULL,
  output_json TEXT,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE run_events (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id),
  sequence INTEGER NOT NULL,
  type TEXT NOT NULL,
  node_id TEXT,
  message_id TEXT,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(run_id, sequence)
);

CREATE TABLE approvals (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id),
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  request_json TEXT NOT NULL,
  resolution_json TEXT,
  created_at TEXT NOT NULL,
  resolved_at TEXT
);

CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id),
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  path TEXT,
  content_type TEXT,
  metadata_json TEXT NOT NULL,
  version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

MVP 可用 SQLite；需要多实例时迁移 PostgreSQL。不要把数据库内容继续重复写成多个互相不一致的 JSON Snapshot。

---

## 18.28 测试代码补充

### Event Repository

```python
@pytest.mark.asyncio
async def test_event_sequence_is_monotonic(tmp_path):
    repo = EventRepository(tmp_path / "test.db")
    publisher = EventPublisher(repo)

    first = await publisher.publish(
        run_id="run-1",
        event_type=RunEventType.RUN_STARTED,
    )
    second = await publisher.publish(
        run_id="run-1",
        event_type=RunEventType.NODE_STARTED,
        node_id="parse_paper",
    )

    assert first.sequence == 1
    assert second.sequence == 2
    assert [x.sequence for x in repo.list_after(run_id="run-1")] == [1, 2]
```

### SSE reconnect

```python
@pytest.mark.asyncio
async def test_sse_replays_events_after_sequence(client, event_publisher):
    await event_publisher.publish(
        run_id="run-1", event_type=RunEventType.RUN_STARTED
    )
    await event_publisher.publish(
        run_id="run-1",
        event_type=RunEventType.NODE_STARTED,
        node_id="planner",
    )

    async with client.stream("GET", "/api/runs/run-1/events?after=1") as response:
        assert response.status_code == 200
        text = ""
        async for chunk in response.aiter_text():
            text += chunk
            if "node.started" in text:
                break

    assert '"sequence":2' in text
    assert '"node_id":"planner"' in text
```

### Reducer

```typescript
import { describe, expect, it } from "vitest";
import { initialRunState, reduceRunEvent } from "./event-reducer";

describe("reduceRunEvent", () => {
  it("appends streamed deltas in sequence", () => {
    let state = reduceRunEvent(initialRunState, {
      id: "1",
      run_id: "run",
      sequence: 1,
      type: "message.created",
      message_id: "m1",
      payload: { role: "assistant" },
    });
    state = reduceRunEvent(state, {
      id: "2",
      run_id: "run",
      sequence: 2,
      type: "message.delta",
      message_id: "m1",
      payload: { delta: "Hello " },
    });
    state = reduceRunEvent(state, {
      id: "3",
      run_id: "run",
      sequence: 3,
      type: "message.delta",
      message_id: "m1",
      payload: { delta: "world" },
    });

    expect(state.messages.m1.content).toBe("Hello world");
    expect(state.lastSequence).toBe(3);
  });

  it("ignores duplicate events", () => {
    const event = {
      id: "1",
      run_id: "run",
      sequence: 1,
      type: "run.started",
      payload: {},
    };
    const state = reduceRunEvent(initialRunState, event);
    expect(reduceRunEvent(state, event)).toBe(state);
  });
});
```

### Approval Resume

```python
@pytest.mark.asyncio
async def test_edited_commands_are_used_after_resume(graph, config):
    task = asyncio.create_task(
        graph.ainvoke(
            {
                "run_id": "r1",
                "command_plans": [
                    {"command": "python train.py", "risk": "review"}
                ],
            },
            config=config,
        )
    )

    await wait_until_interrupted(graph, config)
    await graph.ainvoke(
        Command(
            resume={
                "decision": "approve",
                "edited_commands": [
                    {"command": "python train.py --smoke-test", "risk": "safe"}
                ],
            }
        ),
        config=config,
    )

    snapshot = await graph.aget_state(config)
    assert snapshot.values["command_plans"][0]["command"].endswith("--smoke-test")
```

---

## 18.29 CI 直接落地

```yaml
name: ci

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check .
      - run: mypy backend runtime graphs agents tools
      - run: pytest -q

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test -- --run
      - run: npm run build
        env:
          NEXT_PUBLIC_MOCK_MODE: "false"

  integration:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.test.yml up -d --build
      - run: ./scripts/wait-for-health.sh
      - run: pytest tests/integration -q
      - run: docker compose -f docker-compose.test.yml logs
        if: failure()
```

---

## 18.30 最建议先提交的 8 个 PR

### PR 1：事件协议与 Event Store

```text
新增 domain/events.py
新增 event_repository.py
改造 event_service.py
保留旧 WebSocket 兼容层
```

### PR 2：SSE 与前端 reducer

```text
新增 /api/runs/{id}/events
新增 use-run-events.ts
新增 event-reducer.ts
删除关键词推断状态
```

### PR 3：Run 持久化

```text
新增 runs/messages/approvals/artifacts 表
页面刷新保留 run_id
后端重启不删除历史 Run
```

### PR 4：拆分 WorkspaceShell

```text
提取 Composer
提取 MessageList
提取 RunTimeline
提取 ArtifactPanel
入口控制在 150 行以内
```

### PR 5：真正的审批恢复

```text
LangGraph interrupt()
Command(resume=...)
编辑后的命令/计划进入 checkpoint
```

### PR 6：Docker Sandbox

```text
完全移除宿主机执行生成代码
资源限制
网络默认关闭
自动销毁容器
```

### PR 7：真实 Product Build Loop

```text
生成 Next.js 项目
npm ci/typecheck/build
失败自动 patch repair
```

### PR 8：Preview 与浏览器验证

```text
动态 preview container
preview.ready 真实事件
Playwright smoke test
右侧 iframe 显示真实应用
```

完成这 8 个 PR 后，PaperPilot 才会从“流程展示型 Demo”进入“可实际使用的 Agent 工作台”阶段。

