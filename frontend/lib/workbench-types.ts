export type WorkflowStatus =
  | "pending"
  | "running"
  | "success"
  | "waiting_review"
  | "failed"
  | "revised";

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
