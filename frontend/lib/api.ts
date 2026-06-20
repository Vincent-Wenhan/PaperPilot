import type { ArtifactItem, AgentEvent, WorkflowStatus } from "@/lib/mock-data";

const API_BASE =
  process.env.NEXT_PUBLIC_PAPERPILOT_API_BASE ?? "http://localhost:8000";

export type ApiRun = {
  run_id: string;
  project_id: string;
  mode: "reproduce" | "productize";
  status: WorkflowStatus;
  task: string;
  created_at: string;
  updated_at: string;
  summary: string;
  inputs: Record<string, string>;
  result_summary: Record<string, unknown>;
  plan: string[];
};

export type ApiRunCreateRequest = {
  mode: "reproduce" | "productize";
  project_id: string;
  task: string;
  pdf_path?: string;
  github_url?: string;
  hardware?: string;
  gpu_info?: string;
  goal?: string;
  target_user?: string;
  product_goal?: string;
  preferred_type?: string;
  run_pipeline?: boolean;
  api_key?: string;
  base_url?: string;
  model?: string;
  implementation_model?: string;
  mock_mode?: boolean;
};

export type ApiLlmConfig = {
  api_key: string;
  base_url: string;
  model: string;
  implementation_model: string;
};

export type ApiLlmConnectionRequest = {
  api_key: string;
  base_url: string;
  model: string;
  mock_mode: boolean;
};

export type ApiLlmConnectionResult = {
  ok: boolean;
  message: string;
  endpoint: string;
  model: string;
  mock_mode: boolean;
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

export type ApiGraphNode = {
  id: string;
  label: string;
  agent: string;
  status: WorkflowStatus;
  startedAt: string;
  finishedAt: string;
  inputArtifacts: string[];
  outputArtifacts: string[];
  toolCalls: Array<{
    eventId: string;
    type: string;
    message: string;
    payload: Record<string, unknown>;
    timestamp: string;
  }>;
  issues: Array<{
    eventId: string;
    message: string;
    payload: Record<string, unknown>;
  }>;
};

export async function uploadPdf(file: File): Promise<{ pdf_path: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/api/upload/pdf`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`PDF upload failed with ${response.status}`);
  }
  return response.json() as Promise<{ pdf_path: string }>;
}

export async function fetchLlmConfig(): Promise<ApiLlmConfig> {
  const response = await fetch(`${API_BASE}/api/llm/config`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`LLM config API returned ${response.status}`);
  }
  return response.json() as Promise<ApiLlmConfig>;
}

export async function saveLlmConfig(config: ApiLlmConfig): Promise<ApiLlmConfig> {
  const response = await fetch(`${API_BASE}/api/llm/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new Error(`LLM config save failed with ${response.status}`);
  }
  return response.json() as Promise<ApiLlmConfig>;
}

export async function fetchWorkbenchSnapshot() {
  const response = await fetch(`${API_BASE}/api/workbench/mock`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Workbench API returned ${response.status}`);
  }
  return response.json() as Promise<ApiWorkbenchSnapshot>;
}

export async function createRun(request: ApiRunCreateRequest) {
  const response = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Run creation failed with ${response.status}`);
  }
  return response.json() as Promise<ApiRun>;
}

export async function fetchRun(runId: string) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Run API returned ${response.status}`);
  }
  return response.json() as Promise<ApiRun>;
}

export async function fetchRunEvents(runId: string) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/events`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Run events API returned ${response.status}`);
  }
  return response.json() as Promise<ApiEvent[]>;
}

export async function fetchRunGraph(runId: string) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/graph`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Run graph API returned ${response.status}`);
  }
  return response.json() as Promise<ApiGraphNode[]>;
}

export async function testLlmConnection(request: ApiLlmConnectionRequest) {
  const response = await fetch(`${API_BASE}/api/llm/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`LLM test API returned ${response.status}`);
  }
  return response.json() as Promise<ApiLlmConnectionResult>;
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

export async function fetchRunActions(runId: string) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/actions`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Run actions API returned ${response.status}`);
  }
  return response.json() as Promise<ApiAction[]>;
}

export async function fetchPatches(runId: string) {
  const response = await fetch(`${API_BASE}/api/patches/${runId}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Patches API returned ${response.status}`);
  }
  return response.json();
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

export type ApiPatch = {
  patch_id: string;
  run_id: string;
  path: string;
  old_content: string;
  new_content: string;
  unified_diff: string;
  reason: string;
};

export type ApiRunResult = {
  pipeline_status?: string;
  errors?: string[];
  llm_attempts?: number;
  llm_failures?: number;
  report_ready?: boolean;
  run_script_ready?: boolean;
  generated_files?: number;
  product_output_dir?: string;
  detected_problems?: string[];
  revision_suggestions?: string[];
  safety_warnings?: string[];
  [key: string]: unknown;
};

export async function fetchRunResult(runId: string) {
  const response = await fetch(`${API_BASE}/api/runs/${runId}/result`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Run result API returned ${response.status}`);
  }
  return response.json() as Promise<ApiRunResult>;
}
