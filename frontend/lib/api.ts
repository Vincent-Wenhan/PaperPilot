import type { ArtifactItem, AgentEvent, WorkflowStatus } from "@/lib/mock-data";

const API_BASE =
  process.env.NEXT_PUBLIC_PAPERPILOT_API_BASE ?? "http://localhost:8000";

export type ApiRun = {
  run_id: string;
  project_id: string;
  mode: "reproduce" | "productize";
  status: WorkflowStatus;
  task: string;
  summary: string;
  plan: string[];
};

export type ApiEvent = {
  event_id: string;
  run_id: string;
  node: string;
  agent: string;
  event_type: string;
  status: WorkflowStatus;
  message: string;
  created_at: string;
};

export type ApiAction = {
  action_id: string;
  run_id: string;
  agent: string;
  tool: string;
  command: string;
  risk: "low" | "medium" | "high";
  reason: string;
  status: "pending" | "approved" | "rejected" | "edited";
};

export type ApiArtifact = {
  artifact_id: string;
  run_id: string;
  name: string;
  kind: string;
  path: string;
  size_bytes: number;
  status: WorkflowStatus;
};

export type ApiFileNode = {
  path: string;
  name: string;
  kind: "file" | "directory";
  size_bytes: number;
};

export type ApiFileContent = {
  path: string;
  content: string;
  truncated: boolean;
};

export type ApiWorkbenchSnapshot = {
  project_id: string;
  active_run: ApiRun;
  events: ApiEvent[];
  actions: ApiAction[];
  artifacts: ApiArtifact[];
  files: ApiFileNode[];
};

export async function fetchWorkbenchSnapshot() {
  const response = await fetch(`${API_BASE}/api/workbench/mock`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Workbench API returned ${response.status}`);
  }
  return response.json() as Promise<ApiWorkbenchSnapshot>;
}

export async function fetchArtifacts(runId: string) {
  const response = await fetch(`${API_BASE}/api/artifacts/${runId}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Artifact API returned ${response.status}`);
  }
  return response.json() as Promise<ApiArtifact[]>;
}

export async function fetchFiles(runId: string) {
  const response = await fetch(`${API_BASE}/api/files/${runId}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Files API returned ${response.status}`);
  }
  return response.json() as Promise<ApiFileNode[]>;
}

export async function fetchFileContent(runId: string, path: string) {
  const params = new URLSearchParams({ path });
  const response = await fetch(`${API_BASE}/api/files/${runId}/content?${params}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`File content API returned ${response.status}`);
  }
  return response.json() as Promise<ApiFileContent>;
}

export async function approveAction(actionId: string) {
  const response = await fetch(`${API_BASE}/api/actions/${actionId}/approve`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Action approval failed with ${response.status}`);
  }
  return response.json();
}

export async function rejectAction(actionId: string) {
  const response = await fetch(`${API_BASE}/api/actions/${actionId}/reject`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Action rejection failed with ${response.status}`);
  }
  return response.json();
}

export async function editAction(actionId: string, editedCommand: string) {
  const response = await fetch(`${API_BASE}/api/actions/${actionId}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      edited_command: editedCommand,
      reason: "Edited from Workbench preview",
    }),
  });
  if (!response.ok) {
    throw new Error(`Action edit failed with ${response.status}`);
  }
  return response.json();
}

export function eventFromApi(event: ApiEvent): AgentEvent {
  return {
    id: event.event_id,
    time: new Date(event.created_at).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }),
    agent: event.agent,
    eventType: event.event_type,
    message: event.message,
    status: event.status,
  };
}

export function artifactFromApi(artifact: ApiArtifact): ArtifactItem {
  return {
    id: artifact.artifact_id,
    name: artifact.name,
    kind: artifact.kind,
    path: artifact.path,
    status: artifact.status,
  };
}
