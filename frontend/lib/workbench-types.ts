export type WorkflowStatus =
  | "pending"
  | "running"
  | "success"
  | "waiting_review"
  | "failed"
  | "revised";

export type RunMode = "reproduce" | "productize";

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
  runId?: string;
  node?: string;
  time: string;
  createdAt?: string;
  agent: string;
  eventType: string;
  message: string;
  payload?: Record<string, unknown>;
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

export type RunnerActionView = {
  id: string;
  runId?: string;
  agent: string;
  tool: "run_command" | "apply_patch";
  command: string;
  cwd?: string;
  patchId?: string;
  path?: string;
  risk: "low" | "medium" | "high" | "blocked";
  reason: string;
  status?: string;
  executionStatus?: string;
};

export type RunnerReviewView = {
  purpose: string;
  command: string;
  risk: "low" | "medium" | "high";
  cwd: string;
  expectedOutput: string;
  stdout?: string;
  stderr?: string;
  exitCode?: number | null;
};

export type WorkbenchToolCallEvent = {
  id: string;
  runId?: string;
  node?: string;
  agent?: string;
  tool?: string;
  eventType?: string;
  action: string;
  observation: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
  status: WorkflowStatus;
};

export type PatchSyntaxResult = {
  syntaxOk?: boolean;
  failures: Array<{
    path?: string;
    error?: string;
  }>;
};
