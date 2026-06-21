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

export type RunnerActionView = {
  id: string;
  agent: string;
  tool: "run_command" | "apply_patch";
  command: string;
  risk: "low" | "medium" | "high" | "blocked";
  reason: string;
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
  action: string;
  observation: string;
  status: WorkflowStatus;
};
