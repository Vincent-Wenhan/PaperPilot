# PaperPilot 深度质量改造方案

## 0. 文档目标

这份文档不是只修 UI 表面问题，也不是继续堆更多 Agent 名字，而是从当前 PaperPilot 的核心质量瓶颈出发，提出一套更深层的改造方案。

当前项目已经具备：

```text
frontend/       Next.js Workbench
backend/        FastAPI + WebSocket + run/action/file/patch services
graphs/         Reproduce / Productize LangGraph workflows
agents/         Research / Repo / Planner / Builder / Reviewer / Evaluator 等高层 Agent
tools/          repo scan / file / code / runner / code quality / product tester
productize/     static product scaffold and inspector
workspace/runs/ run-scoped outputs
```

所以现在真正要解决的不是“有没有架构”，而是：

```text
1. Agent 输出为什么质量一般？
2. 生成代码为什么经常不可运行？
3. 产品原型为什么模板感强、功能浅？
4. UI 为什么不能充分反映真实流程？
5. 怎么让每一步都有可验证产物，而不是只生成文本？
```

本方案核心目标：

```text
把 PaperPilot 从「能生成报告和 mock 原型的 Agent Workbench」
升级为「产物可验证、失败可修复、流程可观察的 Research Agent IDE」。
```

---

## 1. 当前项目的深层问题

### 1.1 问题不是 Agent 少，而是 Agent 之间缺少“硬接口”

当前项目已经有多个 Agent：

```text
Research Understanding Agent
Repository Understanding Agent
Reproduction Planner Agent
Reproduction Implementation Agent
Code Review Agent
Execution Diagnosis Agent

Research Synthesizer Agent
Product Planner Agent
Prototype Builder Agent
Product Evaluator Agent
```

这些 Agent 的职责表面上是清楚的，但深层问题是：

```text
Agent 之间主要传递“文档式结果”，
而不是传递“可验证 contract / artifact”。
```

例如：

```text
Research Agent 输出 paper understanding
Planner Agent 输出 reproduction plan
Implementation Agent 输出 code bundle
Reviewer Agent 输出 review score
```

这条链路的问题是：

```text
1. Planner 不一定给出可执行的验收条件。
2. Implementation 不一定严格实现 Planner 的关键模块。
3. Reviewer 不一定能把问题转化为可执行 patch。
4. Diagnosis 不一定能把失败路由回正确上游 Agent。
```

因此，Agent 多并不能自然提高质量。  
真正需要的是：

```text
每个 Agent 产出一个有 schema、有验收条件、可被下游验证的 artifact。
```

---

### 1.2 Reproduce Mode 的核心瓶颈：生成代码缺少“可执行合同”

当前 Reproduce Mode 已经有：

```text
Paper Understanding
Repository Understanding
Reproduction Plan
Implementation Blueprint
Generated Code
Sandbox Verify
Code Review
Revision
Diagnosis
```

这条链路方向正确，但质量瓶颈在于：

```text
Implementation Agent 容易生成一个安全、可展示、但不够真实的 scaffold。
```

也就是说，它可能做到：

```text
1. 有 main.py
2. 有 README.md
3. 有 requirements.txt
4. 有 smoke-test
5. 能打印一些结果
```

但不一定做到：

```text
1. 代码结构真的对应论文方法模块。
2. 输入输出真的对应论文任务。
3. repo 中的官方 entrypoint / config / dataset path 被正确利用。
4. 生成代码有 meaningful tests。
5. smoke test 不是空跑，而是验证核心数据流。
6. 失败后能定位到具体文件并自动生成 patch。
```

深层原因：

```text
当前“能不能运行”的定义不够硬。
```

需要引入：

```text
Implementation Contract
Verification Contract
Repair Patch Contract
```

---

### 1.3 Productize Mode 的核心瓶颈：PRD/MVP 不等于好产品

Productize Mode 已经有：

```text
Capability Cards
Method Composition
PRD
MVP / MoSCoW
Prototype Plan
Product Evaluation
Static Scaffold
```

这已经比直接生成 demo 专业很多。但问题是：

```text
PRD 和 MVP 仍然偏文本设计，不能保证最终原型真的好用。
```

典型表现：

```text
1. 产品功能泛泛，如 upload / analyze / report。
2. UI 像模板，不像围绕具体论文能力设计。
3. mock adapter 返回的数据不一定符合真实论文方法。
4. 用户流程不一定能完成一个明确任务。
5. Evaluation 给了分数，但不一定强制修改原型。
```

深层原因：

```text
PRD 后面缺少一层可执行的 Product Contract。
```

也就是：

```text
产品到底接受什么输入？
输出什么结构？
用户完成什么 job？
前端必须有哪些控件？
mock adapter 必须返回哪些字段？
哪些承诺不能出现？
哪些用户流程必须通过测试？
```

---

### 1.4 UI 的核心问题：能显示状态，但不能解释“为什么这么走”

当前 Workbench UI 已经有：

```text
Sidebar
TopBar
Workflow Graph
Activity
Inspector
Code
Diff
Runner
Tool Calls
Logs
Approval
```

这些组件已经接近目标 UI。但用户仍会觉得“不真实”或“流程状态不准”，主要原因是：

```text
UI 展示的是 run 状态，
但不是每个 graph node 的证据、输入、输出、失败原因和修复动作。
```

例如，用户看到：

```text
Prototype Builder running
Evaluator pending
```

但不一定知道：

```text
Prototype Builder 读取了哪些 artifacts？
写了哪些文件？
调用了哪些 tools？
哪些检查失败？
Evaluator 为什么打低分？
低分后下一步是谁负责修？
```

因此 UI 不只是要“好看”，还要成为：

```text
Agent 运行时的 observability layer。
```

---

### 1.5 当前测试更偏“项目能构建”，还不够“产物能完成任务”

当前项目已有 tests 和 product tester，这是好事。但要提高生成质量，需要区分两类测试：

```text
1. System Tests
   PaperPilot 自己能不能跑。

2. Artifact Tests
   PaperPilot 生成出来的 reproduction code / product prototype 能不能完成任务。
```

现在更缺的是第二类。  
也就是：

```text
每次生成代码或产品后，都要自动生成并运行产物级验收测试。
```

---

## 2. 总体改造方向

建议引入四条“硬闭环”：

```text
1. Evidence Loop
   paper/repo evidence -> structured evidence pack -> confidence

2. Build-Verify-Repair Loop
   generated code -> verifier -> issue -> patch -> verify again

3. Product Contract Loop
   PRD -> product contract -> UI spec -> scaffold -> user-flow test

4. Observable Workflow Loop
   graph node -> structured event -> UI state -> node details -> user approval
```

对应目标：

```text
不是让 LLM 直接“写得更好”，
而是让系统约束 LLM 的输出、验证它、失败后局部修复。
```

---

## 3. Reproduce Mode 深度改造方案

### 3.1 新增 Evidence Pack

当前 Repository Understanding 应该从“总结 repo”升级为生成一个明确的 Evidence Pack。

建议新增 schema：

```python
from pydantic import BaseModel, Field
from typing import Literal


class EvidenceItem(BaseModel):
    source_type: Literal["paper", "repo", "config", "code", "readme"]
    path: str = ""
    quote_or_summary: str
    confidence: Literal["low", "medium", "high"] = "medium"


class RepoEntrypoint(BaseModel):
    path: str
    command_hint: str = ""
    args: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"


class ReproductionEvidencePack(BaseModel):
    task_type: str
    method_modules: list[str]
    datasets: list[EvidenceItem]
    metrics: list[EvidenceItem]
    dependencies: list[str]
    entrypoints: list[RepoEntrypoint]
    configs: list[str]
    checkpoints: list[EvidenceItem]
    missing_evidence: list[str]
    overall_confidence: Literal["low", "medium", "high"]
```

作用：

```text
1. Planner 不再直接读散乱 repo summary。
2. Planner 只基于 evidence pack 做 reproduction plan。
3. 如果 evidence confidence 低，系统应该降级为 paper-only / pseudo implementation，而不是假装完整复现。
```

---

### 3.2 新增 Implementation Contract

在 Implementation Agent 生成代码前，先由 Planner 生成 Implementation Contract。

```python
class ImplementationContract(BaseModel):
    task_name: str
    input_schema: dict
    output_schema: dict
    required_modules: list[str]
    required_files: list[str]
    required_cli: list[str]
    required_tests: list[str]
    smoke_test_command: str
    non_goals: list[str]
    evidence_links: list[str]
```

例子：

```text
required_modules:
  - data_loader
  - model_stub_or_adapter
  - inference
  - metrics
  - report_writer

required_cli:
  - python main.py --smoke-test
  - python main.py --input examples/sample.json --output outputs/result.json

required_tests:
  - tests/test_cli.py
  - tests/test_output_schema.py
  - tests/test_metrics_shape.py
```

核心原则：

```text
Implementation Agent 必须实现 contract；
Verifier 必须按 contract 验收。
```

---

### 3.3 新增 GeneratedProjectVerifier

当前 code quality / tester 更偏静态检查。建议新增一个更硬的 verifier：

```text
tools/generated_project_verifier.py
```

核心能力：

```text
1. 检查 required files 是否存在。
2. 编译所有 Python 文件。
3. pytest --collect-only。
4. 执行 smoke_test_command。
5. 检查 output_schema。
6. 检查是否有 placeholder / fake claims。
7. 返回结构化 VerificationReport。
```

示例代码：

```python
from __future__ import annotations

import json
import py_compile
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VerificationIssue:
    code: str
    message: str
    file: str = ""
    severity: str = "medium"


@dataclass
class VerificationReport:
    ok: bool
    syntax_ok: bool
    tests_collect_ok: bool
    smoke_ok: bool
    schema_ok: bool
    issues: list[VerificationIssue] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""


class GeneratedProjectVerifier:
    def __init__(self, project_dir: Path, contract: dict, timeout: int = 20) -> None:
        self.project_dir = project_dir.resolve()
        self.contract = contract
        self.timeout = timeout

    def verify(self) -> VerificationReport:
        issues: list[VerificationIssue] = []

        files_ok = self._check_required_files(issues)
        syntax_ok = self._check_python_syntax(issues)
        tests_collect_ok = self._pytest_collect(issues)
        smoke_ok, stdout, stderr = self._run_smoke(issues)
        schema_ok = self._check_output_schema(issues)

        return VerificationReport(
            ok=files_ok and syntax_ok and tests_collect_ok and smoke_ok and schema_ok,
            syntax_ok=syntax_ok,
            tests_collect_ok=tests_collect_ok,
            smoke_ok=smoke_ok,
            schema_ok=schema_ok,
            issues=issues,
            stdout=stdout,
            stderr=stderr,
        )

    def _check_required_files(self, issues: list[VerificationIssue]) -> bool:
        ok = True
        for rel in self.contract.get("required_files", []):
            if not (self.project_dir / rel).exists():
                ok = False
                issues.append(
                    VerificationIssue(
                        code="missing_required_file",
                        file=rel,
                        message=f"Required file is missing: {rel}",
                        severity="high",
                    )
                )
        return ok

    def _check_python_syntax(self, issues: list[VerificationIssue]) -> bool:
        ok = True
        for path in self.project_dir.rglob("*.py"):
            if any(part in {".git", "__pycache__", ".venv"} for part in path.parts):
                continue
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                ok = False
                issues.append(
                    VerificationIssue(
                        code="syntax_error",
                        file=str(path.relative_to(self.project_dir)),
                        message=str(exc),
                        severity="high",
                    )
                )
        return ok

    def _pytest_collect(self, issues: list[VerificationIssue]) -> bool:
        tests_dir = self.project_dir / "tests"
        if not tests_dir.exists():
            issues.append(
                VerificationIssue(
                    code="missing_tests",
                    message="No tests/ directory found.",
                    severity="medium",
                )
            )
            return False

        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            issues.append(
                VerificationIssue(
                    code="pytest_collect_failed",
                    message=result.stderr[-2000:] or result.stdout[-2000:],
                    severity="high",
                )
            )
            return False
        return True

    def _run_smoke(self, issues: list[VerificationIssue]) -> tuple[bool, str, str]:
        command = self.contract.get("smoke_test_command") or "python main.py --smoke-test"
        result = subprocess.run(
            command.split(),
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            issues.append(
                VerificationIssue(
                    code="smoke_failed",
                    message=result.stderr[-2000:] or result.stdout[-2000:],
                    severity="high",
                )
            )
            return False, result.stdout, result.stderr
        return True, result.stdout, result.stderr

    def _check_output_schema(self, issues: list[VerificationIssue]) -> bool:
        expected = self.contract.get("output_schema") or {}
        if not expected:
            return True

        output_path = self.project_dir / "outputs" / "result.json"
        if not output_path.exists():
            issues.append(
                VerificationIssue(
                    code="missing_output_json",
                    file="outputs/result.json",
                    message="Smoke test did not produce outputs/result.json.",
                    severity="high",
                )
            )
            return False

        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(
                VerificationIssue(
                    code="invalid_output_json",
                    file="outputs/result.json",
                    message=str(exc),
                    severity="high",
                )
            )
            return False

        missing = [key for key in expected if key not in data]
        if missing:
            issues.append(
                VerificationIssue(
                    code="output_schema_mismatch",
                    file="outputs/result.json",
                    message=f"Missing output fields: {missing}",
                    severity="high",
                )
            )
            return False

        return True
```

---

### 3.4 Graph 改为 Build-Verify-Repair Loop

当前 Reproduce graph 已经有 review/revision，但建议进一步明确成：

```text
implementation_contract
  ↓
implementation_generation
  ↓
materialize_project
  ↓
generated_project_verifier
  ↓
if failed:
    code_repair_agent
    apply_patch
    verify again
  ↓
code_review
  ↓
final diagnosis
```

路由函数：

```python
def route_after_verification(state: dict) -> str:
    report = state.get("verification_report") or {}
    if report.get("ok"):
        return "code_review"

    repair_count = int(state.get("repair_count") or 0)
    if repair_count >= 2:
        return "execution_diagnosis"

    return "code_repair"
```

---

### 3.5 Repair Agent 只生成 Patch，不重新生成整个项目

LLM 重新生成整个项目容易破坏已有正确部分。  
建议 Repair Agent 只输入：

```text
contract
verification_report
current_files
code_review_issues
```

输出：

```python
class CodePatch(BaseModel):
    path: str
    new_content: str
    reason: str
    fixes: list[str]


class CodePatchBundle(BaseModel):
    summary: str
    patches: list[CodePatch]
    expected_fixed_issues: list[str]
```

应用 patch 后重新 verifier。

---

## 4. Productize Mode 深度改造方案

### 4.1 在 PRD 后新增 Product Contract

PRD 是产品需求文档，但它不是可执行验收标准。  
建议新增：

```text
ProductContract
```

schema：

```python
from pydantic import BaseModel, Field
from typing import Literal


class ProductIOContract(BaseModel):
    input_type: Literal["image", "text", "video", "file", "mixed"]
    input_fields: list[str]
    output_fields: list[str]
    example_input: dict
    example_output: dict


class ProductUXContract(BaseModel):
    primary_user_action: str
    required_controls: list[str]
    required_result_cards: list[str]
    empty_state: str
    loading_state: str
    error_state: str


class ProductSafetyContract(BaseModel):
    forbidden_claims: list[str]
    required_disclaimers: list[str]
    mock_mode_boundary: str


class ProductContract(BaseModel):
    product_name: str
    target_user: str
    job_to_be_done: str
    io: ProductIOContract
    ux: ProductUXContract
    safety: ProductSafetyContract
    acceptance_tests: list[str]
```

这会让 Productize 不再只是“生成 PRD + mock UI”，而是：

```text
PRD -> ProductContract -> UI Spec -> deterministic scaffold -> user-flow test
```

---

### 4.2 Prototype Builder 只生成 UI Spec，不直接自由写代码

建议把 Prototype Builder 的职责改为：

```text
输入：
  ProductContract
  PRD
  MVP Scope
  Capability Cards

输出：
  StaticUISpec
  MockAdapterSpec
```

而不是让 LLM 自由生成完整 UI 代码。

示例：

```python
class UIControl(BaseModel):
    id: str
    label: str
    type: Literal["textarea", "file", "select", "slider", "checkbox"]
    required: bool = True
    placeholder: str = ""


class ResultCard(BaseModel):
    id: str
    title: str
    fields: list[str]


class StaticUISpec(BaseModel):
    title: str
    subtitle: str
    controls: list[UIControl]
    result_cards: list[ResultCard]
    primary_button: str
    layout: Literal["single_panel", "two_column", "dashboard", "report"]
```

然后由 deterministic compiler 生成：

```text
index.html
app.js
adapter.js
styles.css
README.md
product_spec.md
```

这样产品质量会更稳定。

---

### 4.3 Product Tester 升级为 User-flow Tester

当前 product tester 可以检查文件和静态结构。  
建议增加用户流程级检查：

```text
1. index.html 存在。
2. app.js 存在。
3. adapter.js 提供 mock analyze 函数。
4. UI 包含 contract.required_controls。
5. mock output 包含 contract.output_fields。
6. README 能说明如何运行。
7. 不出现 forbidden_claims。
```

如果后续能加 Playwright，可以再做：

```text
1. 打开 index.html。
2. 输入 example_input。
3. 点击 primary button。
4. 检查 result card 出现。
5. 检查 output fields 出现。
```

第一版可以不引入 Playwright，先用静态 HTML/JS 检查。

---

### 4.4 Product Evaluator 改为阻断式验收

当前 evaluator 如果只是评分，不能保证产品变好。  
建议把 evaluation 变成：

```text
blocking issues
non-blocking warnings
revision route
```

schema：

```python
class ProductIssue(BaseModel):
    issue_id: str
    category: Literal[
        "paper_faithfulness",
        "user_value",
        "mvp_scope",
        "mock_boundary",
        "ui_usability",
        "technical_feasibility",
        "safety",
    ]
    severity: Literal["low", "medium", "high"]
    blocking: bool
    message: str
    suggested_route: Literal[
        "revise_prd",
        "reduce_mvp_scope",
        "revise_prototype",
        "accept_with_warning",
    ]


class ProductVerificationReport(BaseModel):
    ok: bool
    score: float
    issues: list[ProductIssue]
    revision_route: str
```

路由：

```python
def route_after_product_evaluation(state: dict) -> str:
    report = state.get("product_verification") or {}
    issues = report.get("issues") or []
    blocking = [issue for issue in issues if issue.get("blocking")]

    if not blocking and float(report.get("score") or 0) >= 4:
        return "finish"

    if int(state.get("revision_count") or 0) >= 2:
        return "finish_with_warnings"

    routes = [issue.get("suggested_route") for issue in blocking]
    if "revise_prototype" in routes:
        return "revise_prototype"
    if "reduce_mvp_scope" in routes:
        return "revise_product_plan"
    return "revise_product_plan"
```

---

## 5. Agent 协作结构改造

### 5.1 不增加 Agent 数量，增加 Artifact 质量

建议明确每个 Agent 的输入输出：

| Agent | 输入 | 输出 | 验证器 |
|---|---|---|---|
| Research Agent | PDF text | PaperUnderstanding | completeness check |
| Repository Agent | repo files | EvidencePack | evidence confidence check |
| Planner Agent | PaperUnderstanding + EvidencePack | ImplementationContract | contract completeness |
| Implementation Agent | ImplementationContract | GeneratedProject | project verifier |
| Code Review Agent | GeneratedProject + Verifier Report | CodeIssues | issue schema check |
| Repair Agent | CodeIssues + Files | PatchBundle | patch verifier |
| Product Planner | CapabilityCards | PRD + ProductContract | product contract check |
| Prototype Builder | ProductContract | StaticUISpec | UI spec checker |
| Scaffold Compiler | StaticUISpec | StaticBundle | product tester |
| Product Evaluator | StaticBundle + Contract | ProductIssues | blocking route |

核心：

```text
Agent 之间不靠自由聊天。
Agent 之间只靠 schema artifact 交接。
每个 artifact 都必须被 verifier 检查。
```

---

### 5.2 增加 Agent Budget 和 Stop Rule

为避免 over-looping 和乱修：

```python
class AgentBudget(BaseModel):
    max_tool_calls: int = 8
    max_repair_rounds: int = 2
    max_revision_rounds: int = 2
    require_artifact_each_round: bool = True
```

每轮必须产出：

```text
1. artifact
2. verification result
3. next route
```

没有 artifact 的 tool loop 直接停止。

---

## 6. UI 深度改造方案

### 6.1 UI 不只显示状态，要显示因果链

当前目标 UI 应该显示：

```text
Node
  input artifacts
  tool calls
  output artifacts
  issues
  next route
```

建议前端节点详情：

```ts
type NodeDetail = {
  nodeId: string;
  agent: string;
  status: NodeStatus;
  inputArtifacts: ArtifactRef[];
  outputArtifacts: ArtifactRef[];
  toolCalls: ToolCallEvent[];
  issues: IssueRef[];
  routeReason?: string;
};
```

点击 workflow node 时，右侧 Inspector 显示：

```text
Why this node ran
What it read
What it wrote
What failed
Where it routed next
```

---

### 6.2 统一 Icon Registry

当前图标风格如果分散在各组件中，容易不一致。  
建议新增：

```text
frontend/lib/icons.tsx
```

```tsx
import {
  Bot,
  Boxes,
  ClipboardCheck,
  Code2,
  FileText,
  FolderGit2,
  GitBranch,
  Hammer,
  LayoutDashboard,
  ListChecks,
  Play,
  Search,
  ShieldCheck,
  Terminal,
  UserCheck,
} from "lucide-react";

export const icons = {
  projects: Boxes,
  papers: FileText,
  repos: FolderGit2,
  runs: Play,
  agents: Bot,
  settings: LayoutDashboard,

  parse_paper: FileText,
  research_understanding: Search,
  prepare_repository: FolderGit2,
  repository_understanding: GitBranch,
  reproduction_planner: ListChecks,
  reproduction_implementation: Code2,
  sandbox_verify: ShieldCheck,
  code_review: ClipboardCheck,
  code_revise: Hammer,
  execution_diagnosis: Terminal,

  product_planner: ListChecks,
  prototype_builder: Code2,
  product_evaluator: ClipboardCheck,
  approval: UserCheck,
};
```

所有 sidebar / workflow / inspector 都从这里取图标。

---

### 6.3 前端状态 reducer

Workflow UI 不应该每个组件自己推断状态。  
建议统一：

```text
frontend/lib/workflow-state.ts
```

```ts
export type NodeStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "waiting_review"
  | "revised";

export type WorkflowNodeView = {
  id: string;
  label: string;
  agent: string;
  status: NodeStatus;
  startedAt?: string;
  finishedAt?: string;
  durationMs?: number;
  issueCount: number;
  artifactCount: number;
};

export function reduceEventsToNodes(
  template: WorkflowNodeView[],
  events: ApiEvent[],
): WorkflowNodeView[] {
  const byId = new Map(template.map((node) => [node.id, { ...node }]));

  for (const event of events) {
    const nodeId = event.node;
    const node = byId.get(nodeId);
    if (!node) continue;

    if (event.event_type === "node_started") {
      node.status = "running";
      node.startedAt = event.created_at;
    }

    if (event.event_type === "node_finished") {
      node.status = "success";
      node.finishedAt = event.created_at;
    }

    if (event.event_type === "node_failed") {
      node.status = "failed";
      node.finishedAt = event.created_at;
    }

    if (event.event_type === "human_review_required") {
      node.status = "waiting_review";
    }

    if (event.event_type === "revision_started") {
      node.status = "revised";
    }

    if (event.event_type === "evaluation_issue") {
      node.issueCount += 1;
    }

    if (event.event_type === "artifact_created") {
      node.artifactCount += 1;
    }
  }

  return [...byId.values()];
}
```

---

### 6.4 Approval Card 显示真实风险

Approval card 应该显示：

```text
Action
Files affected
Risk reason
Expected effect
Approve / Edit / Reject
```

统一 payload：

```ts
type PendingActionPayload = {
  command?: string;
  patchId?: string;
  files?: string[];
  cwd?: string;
  expectedEffect?: string;
  riskReason?: string;
};
```

这样用户才知道为什么需要审批。

---

## 7. 工程基础问题

### 7.1 requirements.txt / ci.yml 格式

当前 raw 页面显示 `requirements.txt` 是单行，`ci.yml` 也显示异常单行。建议本地确认并修成标准格式。否则安装和 CI 可能失败。

requirements 推荐：

```txt
fastapi>=0.115,<1
uvicorn[standard]>=0.30,<1
PyMuPDF>=1.24,<2
openai>=1.50,<2
socksio>=1.0,<2
pydantic>=2.0,<3
python-dotenv>=1.0,<2
python-multipart>=0.0.9,<1
langgraph>=0.2,<2
pyyaml>=6,<7
pytesseract>=0.3,<1
```

CI 推荐：

```yaml
name: CI

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
      - name: Install Python deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Python syntax
        run: |
          python -m compileall main.py config.py
          python -m compileall agents tools pipeline productize schemas runtime graphs backend
      - name: Tests
        run: pytest tests/ -q

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Frontend build
        run: |
          cd frontend
          npm ci
          npm run build
```

---

## 8. 分阶段实施计划

### Phase 1：质量基线修复

```text
1. 修 requirements / CI。
2. 本地跑通 backend + frontend。
3. 增加 Artifact-level test。
4. Reproduce 输出必须通过 GeneratedProjectVerifier。
```

交付标准：

```text
pip install 成功
pytest 成功
npm build 成功
最小 reproduction code 通过 smoke + pytest collect
```

---

### Phase 2：Reproduce Build-Verify-Repair

```text
1. 新增 EvidencePack。
2. 新增 ImplementationContract。
3. 新增 GeneratedProjectVerifier。
4. 新增 CodeRepairAgent。
5. Graph 改成 verify -> repair -> verify loop。
```

交付标准：

```text
失败不是只给报告，而是生成 patch 并重新验证。
```

---

### Phase 3：Productize Product Contract

```text
1. PRD 后新增 ProductContract。
2. PrototypeBuilder 只输出 StaticUISpec。
3. Scaffold compiler 根据 spec 生成产品。
4. Product tester 验收 UI controls / result cards / mock output schema。
5. Product evaluator 输出 blocking issues。
```

交付标准：

```text
生成产品不是泛泛模板，而是符合 ProductContract 的可验收原型。
```

---

### Phase 4：UI Observability

```text
1. 所有 graph node emit structured events。
2. 前端 reducer 统一生成 node status。
3. Node detail 展示 inputs / outputs / tools / issues / route.
4. Tool Calls 按 node 分组。
5. Approval card 显示真实风险和影响文件。
6. Icon registry 统一图标。
```

交付标准：

```text
UI 能解释 Agent 为什么做这一步、读了什么、写了什么、为什么失败、下一步去哪。
```

---

## 9. 最小可交付版本 v2

建议把下一版目标定义为：

```text
PaperPilot v2: Verifiable Research Agent IDE
```

必须满足：

```text
1. README 安装命令真实可跑。
2. Reproduce 生成代码必须通过 GeneratedProjectVerifier。
3. 失败时至少尝试 1 次 patch repair。
4. Productize 必须生成 ProductContract。
5. 产品原型必须通过 ProductContract tester。
6. UI workflow node 状态来自 structured events。
7. Tool calls / artifacts / issues 和 node 绑定。
8. Approval card 显示真实 action 风险。
9. 生成失败时给出可解释 diagnosis，而不是假装成功。
```

---

## 10. 总结

当前 PaperPilot 已经有比较完整的 Agent Workbench 基础，但质量问题的根源不是 UI 组件缺少，也不是 Agent 数量不够，而是：

```text
1. Agent 输出缺少硬 contract。
2. 生成代码缺少产物级 verifier。
3. 产品设计缺少 ProductContract。
4. 修复过程缺少 patch-level repair loop。
5. UI 缺少“因果解释层”，不能展示每个节点的输入、输出、工具和失败原因。
```

下一步最关键的三个改动：

```text
1. GeneratedProjectVerifier
   让生成代码必须真的跑。

2. ProductContract + StaticUISpec
   让产品原型从 PRD 文本变成可验收产品。

3. Event-driven Node Detail UI
   让 UI 真实解释 Agent 流程，而不是只显示状态。
```

这三件事完成后，PaperPilot 的质量会明显提升：  
它会从“能展示 Agent 流程的 demo”变成“能生成、验证、修复、解释结果的 Research Agent IDE”。
