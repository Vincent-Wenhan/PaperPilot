/**
 * Run event reducer for the PaperPilot workbench.
 *
 * The reducer is the single source of truth for run state on the client.
 * Events are applied idempotently: stale, duplicate, or out-of-order
 * events are ignored.
 *
 * The reducer is intentionally pure and side-effect free.  Persistence
 * and SSE transport live in `use-run-events.ts` and `api-client.ts`.
 */

export type RunStatus =
  | "queued"
  | "running"
  | "waiting_input"
  | "waiting_approval"
  | "succeeded"
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
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  status: "streaming" | "completed" | "failed";
  agent?: string;
  node?: string;
}

export interface RunEvent {
  event_id: string;
  run_id: string;
  sequence: number;
  event_type: string;
  node?: string;
  agent?: string;
  status?: string;
  message?: string;
  payload: Record<string, any>;
  created_at: string;
}

export interface ApprovalView {
  approval_id: string;
  title: string;
  kind: string;
  risk_level?: string;
  reason?: string;
  commands?: Array<{ command: string; risk: string; reason: string }>;
  patch?: string;
  expected_effect?: string;
}

export interface ArtifactView {
  artifact_id: string;
  run_id: string;
  kind: string;
  name: string;
  path: string;
  size_bytes: number;
  status?: string;
}

export interface RunViewState {
  runId: string;
  status: RunStatus;
  lastSequence: number;
  nodes: Record<string, NodeStatus>;
  nodeOrder: string[];
  messages: Record<string, StreamMessage>;
  messageOrder: string[];
  approvals: Record<string, ApprovalView>;
  artifacts: Record<string, ArtifactView>;
  artifactOrder: string[];
  preview: {
    status: "idle" | "starting" | "ready" | "failed";
    url?: string;
    error?: string;
  };
  error: string | null;
}

export const initialRunState: RunViewState = {
  runId: "",
  status: "queued",
  lastSequence: 0,
  nodes: {},
  nodeOrder: [],
  messages: {},
  messageOrder: [],
  approvals: {},
  artifacts: {},
  artifactOrder: [],
  preview: { status: "idle" },
  error: null,
};

export function createInitialRunState(runId: string): RunViewState {
  return { ...initialRunState, runId };
}

export function applyRunEvent(
  state: RunViewState,
  event: RunEvent,
): RunViewState {
  if (event.sequence <= state.lastSequence) return state;

  const next: RunViewState = {
    ...state,
    lastSequence: event.sequence,
    nodes: { ...state.nodes },
    nodeOrder: [...state.nodeOrder],
    messages: { ...state.messages },
    messageOrder: [...state.messageOrder],
    approvals: { ...state.approvals },
    artifacts: { ...state.artifacts },
    artifactOrder: [...state.artifactOrder],
    preview: { ...state.preview },
  };

  if (event.node && !next.nodes[event.node]) {
    next.nodes[event.node] = "pending";
  }

  switch (event.event_type) {
    case "run.created":
      next.status = "queued";
      break;
    case "run.started":
      next.status = "running";
      if (event.node) next.nodes[event.node] = "running";
      break;
    case "run.status_changed":
      next.status = (event.payload.status as RunStatus) ?? next.status;
      break;
    case "run.completed":
      next.status = "succeeded";
      break;
    case "run.failed":
      next.status = "failed";
      next.error = event.payload.error ?? event.message ?? "Run failed";
      break;
    case "run.cancelled":
      next.status = "cancelled";
      break;

    case "node.started":
      if (event.node) {
        next.nodes[event.node] = "running";
        if (!next.nodeOrder.includes(event.node)) {
          next.nodeOrder.push(event.node);
        }
      }
      break;
    case "node.progress":
      if (event.node) next.nodes[event.node] = "running";
      break;
    case "node.completed":
      if (event.node) next.nodes[event.node] = "completed";
      break;
    case "node.failed":
      if (event.node) next.nodes[event.node] = "failed";
      break;

    case "message.created": {
      const id = event.payload.message_id ?? event.node ?? "";
      if (!id) break;
      next.messages[id] = {
        id,
        role: event.payload.role ?? "assistant",
        content: event.payload.content ?? "",
        status: "streaming",
        agent: event.agent,
        node: event.node,
      };
      if (!next.messageOrder.includes(id)) {
        next.messageOrder.push(id);
      }
      break;
    }
    case "message.delta": {
      const id = event.payload.message_id ?? "";
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
      const id = event.payload.message_id ?? "";
      const current = next.messages[id];
      if (current) {
        next.messages[id] = { ...current, status: "completed" };
      }
      break;
    }

    case "tool.started":
    case "tool.output":
    case "tool.completed":
    case "tool.failed":
      // Tools are surfaced as assistant messages with structured payload.
      break;

    case "approval.required": {
      const approval: ApprovalView = {
        approval_id: event.payload.approval_id,
        title: event.payload.title ?? "Approval required",
        kind: event.payload.kind ?? "command",
        risk_level: event.payload.risk_level,
        reason: event.payload.reason,
        commands: event.payload.commands,
        patch: event.payload.patch,
        expected_effect: event.payload.expected_effect,
      };
      next.approvals[approval.approval_id] = approval;
      next.status = "waiting_approval";
      break;
    }
    case "approval.resolved": {
      const id = event.payload.approval_id;
      delete next.approvals[id];
      if (Object.keys(next.approvals).length === 0) {
        next.status = "running";
      }
      break;
    }

    case "artifact.created":
    case "artifact.updated": {
      const artifact: ArtifactView = {
        artifact_id: event.payload.artifact_id,
        run_id: event.run_id,
        kind: event.payload.kind ?? "file",
        name: event.payload.name ?? "",
        path: event.payload.path ?? "",
        size_bytes: Number(event.payload.size_bytes ?? 0),
        status: event.payload.status,
      };
      const exists = Boolean(next.artifacts[artifact.artifact_id]);
      next.artifacts[artifact.artifact_id] = artifact;
      if (!exists) next.artifactOrder.push(artifact.artifact_id);
      break;
    }

    case "preview.starting":
      next.preview = { status: "starting" };
      break;
    case "preview.ready":
      next.preview = {
        status: "ready",
        url: event.payload.url,
      };
      break;
    case "preview.failed":
      next.preview = {
        status: "failed",
        error: event.payload.error ?? "Preview failed",
      };
      break;

    default:
      break;
  }

  return next;
}
