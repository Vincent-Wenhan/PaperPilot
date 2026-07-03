import type { WorkflowStatus } from "@/lib/workbench-types";

export type ApiEvent = {
  event_id: string;
  run_id: string;
  node: string;
  agent: string;
  event_type: string;
  status: WorkflowStatus;
  message: string;
  payload?: Record<string, unknown>;
  created_at: string;
};

export type WorkflowNodeView = {
  id: string;
  label: string;
  agent: string;
  status: WorkflowStatus;
  startedAt?: string;
  finishedAt?: string;
  durationMs?: number;
  issueCount: number;
  artifactCount: number;
  toolCount: number;
  inputArtifacts?: string[];
  outputArtifacts?: string[];
  issues?: Array<{ eventId: string; message: string; payload: Record<string, unknown> }>;
  toolCalls?: Array<{
    eventId: string;
    type: string;
    message: string;
    payload: Record<string, unknown>;
    timestamp: string;
  }>;
  routeReason?: string;
  nextRoute?: string;
};

export function reduceEventsToNodes(
  template: WorkflowNodeView[],
  events: ApiEvent[],
): WorkflowNodeView[] {
  const byId = new Map(
    template.map((node) => [
      node.id,
      {
        ...node,
        issueCount: 0,
        artifactCount: 0,
        toolCount: 0,
        inputArtifacts: [...(node.inputArtifacts ?? [])],
        outputArtifacts: [...(node.outputArtifacts ?? [])],
        issues: [...(node.issues ?? [])],
        toolCalls: [...(node.toolCalls ?? [])],
        routeReason: node.routeReason ?? "",
        nextRoute: node.nextRoute ?? "",
      },
    ]),
  );

  for (const event of events) {
    const node = byId.get(event.node);
    if (!node) continue;

    const payload = event.payload ?? {};
    if (event.event_type === "node_started") {
      node.status = "running";
      node.startedAt = event.created_at;
    } else if (event.event_type === "node_finished") {
      node.status = "success";
      node.finishedAt = event.created_at;
    } else if (event.event_type === "node_failed") {
      node.status = "failed";
      node.finishedAt = event.created_at;
    } else if (event.event_type === "human_review_required") {
      node.status = "waiting_review";
    } else if (event.event_type === "revision_started") {
      node.status = "revised";
    }

    if (event.event_type === "tool_call" || event.event_type === "tool_result") {
      node.toolCount += 1;
      node.toolCalls?.push({
        eventId: event.event_id,
        type: event.event_type,
        message: event.message,
        payload,
        timestamp: event.created_at,
      });
    }

    if (event.event_type === "artifact_created") {
      node.artifactCount += 1;
      const artifact = firstString(payload.path, payload.name, payload.artifact_id);
      if (artifact) appendUnique(node.outputArtifacts, artifact);
    }

    if (event.event_type === "evaluation_issue" || event.event_type === "review_issue" || event.event_type === "diagnosis_issue") {
      node.issueCount += 1;
      node.issues?.push({
        eventId: event.event_id,
        message: event.message,
        payload,
      });
    }

    appendMany(node.inputArtifacts, payload.input_artifacts);
    appendMany(node.outputArtifacts, payload.output_artifacts);
    const routeReason = firstString(payload.route_reason, payload.reason);
    if (routeReason) node.routeReason = routeReason;
    const nextRoute = firstString(payload.next_route, payload.revision_route);
    if (nextRoute) node.nextRoute = nextRoute;
  }

  return [...byId.values()];
}

function firstString(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value;
  }
  return "";
}

function appendMany(target: string[] | undefined, source: unknown): void {
  if (!Array.isArray(target) || !Array.isArray(source)) return;
  for (const item of source) {
    if (typeof item === "string" && item.trim()) appendUnique(target, item);
  }
}

function appendUnique(target: string[] | undefined, value: string): void {
  if (!target || target.includes(value)) return;
  target.push(value);
}
