export type RunMode = "reproduce" | "productize";

export type WorkflowStatus =
  | "pending"
  | "running"
  | "success"
  | "waiting_review"
  | "failed"
  | "revised";

export type ProjectNavItem = {
  id: string;
  label: string;
  meta: string;
  status: WorkflowStatus;
};

export type PlanStep = {
  id: string;
  label: string;
  enabled: boolean;
  status: WorkflowStatus;
};

export type AgentEvent = {
  id: string;
  time: string;
  agent: string;
  eventType: string;
  message: string;
  status: WorkflowStatus;
};

export type ArtifactItem = {
  id: string;
  name: string;
  kind: string;
  path: string;
  status: WorkflowStatus;
};

export type CodeFile = {
  id: string;
  path: string;
  language: string;
  content: string;
};

export type ToolCall = {
  id: string;
  action: string;
  observation: string;
  status: WorkflowStatus;
};

export type RunnerReview = {
  command: string;
  purpose: string;
  risk: "low" | "medium" | "high";
  cwd: string;
  expectedOutput: string;
  stdout: string;
  stderr: string;
  exitCode: number | null;
  diagnosis: string;
};

export type ApprovalRequest = {
  id: string;
  agent: string;
  tool: "run_command" | "apply_patch";
  command: string;
  risk: "low" | "medium" | "high" | "blocked";
  reason: string;
};

export const activeProject = {
  id: "project_repro_001",
  name: "Vision Transformer Reproduction",
  mode: "Reproduce" as const,
  model: "gpt-4o-mini",
  runStatus: "Waiting for approval",
};

export const projectNavItems: ProjectNavItem[] = [
  {
    id: "paper",
    label: "ViT paper.pdf",
    meta: "parsed, 14 pages",
    status: "success",
  },
  {
    id: "repo",
    label: "github.com/example/vit",
    meta: "static scan ready",
    status: "success",
  },
  {
    id: "run",
    label: "run_2026_0618_a",
    meta: "reproduce workflow",
    status: "waiting_review",
  },
  {
    id: "product",
    label: "Productize draft",
    meta: "mock-first MVP",
    status: "revised",
  },
];

export const planSteps: PlanStep[] = [
  {
    id: "parse",
    label: "Parse paper and extract resource links",
    enabled: true,
    status: "success",
  },
  {
    id: "research",
    label: "Build structured research understanding",
    enabled: true,
    status: "success",
  },
  {
    id: "repo",
    label: "Scan repository entrypoints and dependencies",
    enabled: true,
    status: "success",
  },
  {
    id: "planner",
    label: "Generate reproduction plan and command route",
    enabled: true,
    status: "running",
  },
  {
    id: "approval",
    label: "Review medium-risk command before execution",
    enabled: true,
    status: "waiting_review",
  },
  {
    id: "diagnosis",
    label: "Diagnose execution result and update report",
    enabled: true,
    status: "pending",
  },
];

export const workflowNodes = [
  {
    id: "parse",
    type: "default",
    position: { x: 0, y: 40 },
    data: { label: "Parse Paper", status: "success" },
  },
  {
    id: "research",
    type: "default",
    position: { x: 210, y: 0 },
    data: { label: "Research Understanding", status: "success" },
  },
  {
    id: "repo",
    type: "default",
    position: { x: 210, y: 96 },
    data: { label: "Repo Scan", status: "success" },
  },
  {
    id: "repository",
    type: "default",
    position: { x: 460, y: 96 },
    data: { label: "Repository Understanding", status: "success" },
  },
  {
    id: "planner",
    type: "default",
    position: { x: 720, y: 48 },
    data: { label: "Reproduction Planner", status: "running" },
  },
  {
    id: "review",
    type: "default",
    position: { x: 980, y: 48 },
    data: { label: "Runner Review", status: "waiting_review" },
  },
  {
    id: "diagnosis",
    type: "default",
    position: { x: 1240, y: 48 },
    data: { label: "Execution Diagnosis", status: "pending" },
  },
  {
    id: "report",
    type: "default",
    position: { x: 1500, y: 48 },
    data: { label: "Report Builder", status: "pending" },
  },
];

export const workflowEdges = [
  { id: "parse-research", source: "parse", target: "research" },
  { id: "parse-repo", source: "parse", target: "repo" },
  { id: "repo-repository", source: "repo", target: "repository" },
  { id: "research-planner", source: "research", target: "planner" },
  { id: "repository-planner", source: "repository", target: "planner" },
  { id: "planner-review", source: "planner", target: "review" },
  { id: "review-diagnosis", source: "review", target: "diagnosis" },
  { id: "diagnosis-report", source: "diagnosis", target: "report" },
];

export const agentEvents: AgentEvent[] = [
  {
    id: "evt_01",
    time: "14:20:02",
    agent: "Research Understanding Agent",
    eventType: "node_finished",
    message: "Extracted method modules, objectives, and resource links.",
    status: "success",
  },
  {
    id: "evt_02",
    time: "14:20:16",
    agent: "Repository Understanding Agent",
    eventType: "tool_call",
    message: "code_search('argparse') found train.py and eval.py.",
    status: "success",
  },
  {
    id: "evt_03",
    time: "14:21:04",
    agent: "Reproduction Planner Agent",
    eventType: "human_review_required",
    message: "Command classified as review-required.",
    status: "waiting_review",
  },
];

export const artifacts: ArtifactItem[] = [
  {
    id: "reproduction_plan",
    name: "reproduction_plan.md",
    kind: "Plan",
    path: "outputs/vit/reproduction_plan.md",
    status: "success",
  },
  {
    id: "run_sh",
    name: "run.sh",
    kind: "Runner",
    path: "outputs/vit/run.sh",
    status: "waiting_review",
  },
  {
    id: "report",
    name: "report.md",
    kind: "Report",
    path: "outputs/vit/report.md",
    status: "pending",
  },
  {
    id: "product_spec",
    name: "product_spec.md",
    kind: "PRD",
    path: "generated_product/insight/product_spec.md",
    status: "revised",
  },
];

export const codeFiles: CodeFile[] = [
  {
    id: "main",
    path: "workspace/generated_code/main.py",
    language: "python",
    content:
      "from config import Settings\n\n\ndef smoke_test() -> dict[str, str]:\n    settings = Settings()\n    return {\"status\": \"ok\", \"dataset\": settings.dataset_name}\n\n\nif __name__ == \"__main__\":\n    print(smoke_test())\n",
  },
  {
    id: "adapter",
    path: "generated_product/adapter.py",
    language: "python",
    content:
      "class ModelAdapter:\n    def __init__(self, mock_mode: bool = True):\n        self.mock_mode = mock_mode\n\n    def predict(self, payload):\n        return {\"label\": \"mock result\", \"confidence\": 0.82}\n",
  },
];

export const patchPreview = {
  file: "workspace/generated_code/main.py",
  oldCode:
    "def smoke_test():\n    return {\"status\": \"todo\"}\n\nprint(smoke_test())\n",
  newCode:
    "from config import Settings\n\n\ndef smoke_test() -> dict[str, str]:\n    settings = Settings()\n    return {\"status\": \"ok\", \"dataset\": settings.dataset_name}\n\n\nif __name__ == \"__main__\":\n    print(smoke_test())\n",
};

export const runnerReview: RunnerReview = {
  command: "python main.py --smoke-test",
  purpose: "Validate generated reproduction entrypoint without training.",
  risk: "medium",
  cwd: "workspace/generated_code",
  expectedOutput: "Structured smoke-test status with no dataset download.",
  stdout: "",
  stderr: "",
  exitCode: null,
  diagnosis: "Waiting for approval before running a bounded smoke test.",
};

export const toolCalls: ToolCall[] = [
  {
    id: "tool_01",
    action: 'code_search("argparse")',
    observation: "Found CLI parsing in train.py and eval.py.",
    status: "success",
  },
  {
    id: "tool_02",
    action: 'python_ast_summary("train.py")',
    observation: "functions: main, train_one_epoch, evaluate",
    status: "success",
  },
  {
    id: "tool_03",
    action: 'compileall_check("workspace/generated_code")',
    observation: "Pending user approval for generated code check.",
    status: "waiting_review",
  },
];

export const approvalRequest: ApprovalRequest = {
  id: "act_001",
  agent: "Reproduction Planner Agent",
  tool: "run_command",
  command: "python main.py --smoke-test",
  risk: "medium",
  reason: "Check generated entrypoint with synthetic inputs only.",
};
