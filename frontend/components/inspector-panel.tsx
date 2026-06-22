"use client";

import {
  Code2,
  FileText,
  GitCompare,
  ListChecks,
  Terminal,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  approvalRequest,
  artifacts as mockArtifacts,
  codeFiles,
  patchPreview,
  runnerReview,
  toolCalls as mockToolCalls,
} from "@/lib/mock-data";
import type {
  AgentEvent,
  PatchSyntaxResult,
  RunnerActionView,
  RunnerReviewView,
  WorkbenchToolCallEvent,
} from "@/lib/workbench-types";
import { StatusPill } from "@/components/status-pill";
import {
  artifactFromApi,
  fetchArtifacts,
  fetchFileContent,
  fetchFiles,
  fetchPatches,
  fetchRunActions,
  type ApiAction,
  type ApiFileNode,
  type ApiPatch,
} from "@/lib/api";
import { ArtifactsPanel } from "@/components/inspector/artifacts-panel";
import { CodePanel } from "@/components/inspector/code-panel";
import { DiffPanel } from "@/components/inspector/diff-panel";
import { RunnerPanel } from "@/components/inspector/runner-panel";
import { ToolCallPanel } from "@/components/inspector/tool-call-panel";

type InspectorTab = "artifacts" | "code" | "diff" | "runner" | "tools";

const tabs: Array<{ id: InspectorTab; label: string; icon: LucideIcon }> = [
  { id: "artifacts", label: "Artifacts", icon: FileText },
  { id: "code", label: "Code", icon: Code2 },
  { id: "diff", label: "Diff", icon: GitCompare },
  { id: "runner", label: "Runner", icon: Terminal },
  { id: "tools", label: "Tool Calls", icon: ListChecks },
];

export function InspectorPanel({
  events = [],
  refreshToken = "",
  runId,
  runStatus = "pending",
  preview = true,
}: {
  events?: AgentEvent[];
  refreshToken?: string;
  runId: string;
  runStatus?: "pending" | "running" | "success" | "waiting_review" | "failed" | "revised";
  preview?: boolean;
}) {
  const [activeTab, setActiveTab] = useState<InspectorTab>("code");
  const [activeFileId, setActiveFileId] = useState(preview ? codeFiles[0]?.id ?? "" : "");
  const [artifactRows, setArtifactRows] = useState(preview ? mockArtifacts : []);
  const [apiFiles, setApiFiles] = useState<ApiFileNode[]>([]);
  const [apiFileContent, setApiFileContent] = useState("");
  const [apiPatches, setApiPatches] = useState<ApiPatch[]>([]);
  const [apiActions, setApiActions] = useState<ApiAction[]>([]);
  const [derivedToolCalls, setDerivedToolCalls] = useState<WorkbenchToolCallEvent[]>([]);
  const [patchStatus, setPatchStatus] = useState<
    "waiting_review" | "success" | "failed" | "revised"
  >("waiting_review");
  const [runnerStatus, setRunnerStatus] = useState<
    "waiting_review" | "success" | "failed" | "revised"
  >("waiting_review");
  const [runnerMessage, setRunnerMessage] = useState(runnerReview.diagnosis);

  const activeMockFile = preview
    ? codeFiles.find((file) => file.id === activeFileId) ?? codeFiles[0]
    : undefined;
  const activeApiFile = apiFiles.find((file) => file.path === activeFileId);
  const activeFile = activeApiFile
    ? {
        id: activeApiFile.path,
        path: activeApiFile.path,
        language: activeApiFile.path.endsWith(".py") ? "python" : "text",
        content: apiFileContent,
      }
    : activeMockFile;

  // Determine which patch to show in DiffPanel
  const activePatch = apiPatches[0] ?? null;

  // Derive tool calls from events
  useEffect(() => {
    const calls: WorkbenchToolCallEvent[] = events
      .filter((e) => e.eventType === "tool_call" || e.eventType === "tool_result")
      .map((e) => ({
        id: e.id,
        runId: e.runId,
        node: e.node,
        agent: e.agent,
        tool: toolNameFromPayload(e.payload) || e.eventType,
        eventType: e.eventType,
        action: e.eventType === "tool_call" ? e.message : "",
        observation: e.eventType === "tool_result" ? e.message : "",
        payload: e.payload,
        timestamp: e.createdAt,
        status: e.status,
      }));
    // Merge paired tool_call/tool_result events
    const byPrefix = new Map<string, WorkbenchToolCallEvent>();
    for (const call of calls) {
      const base = call.id.replace(/_(call|result)$/, "");
      if (byPrefix.has(base)) {
        const existing = byPrefix.get(base)!;
        if (call.action) existing.action = call.action;
        if (call.observation) existing.observation = call.observation;
      } else {
        byPrefix.set(base, { ...call });
      }
    }
    setDerivedToolCalls([...byPrefix.values()]);
  }, [events]);

  useEffect(() => {
    let cancelled = false;
    if (!runId) {
      setArtifactRows(preview ? mockArtifacts : []);
      setApiFiles([]);
      setApiFileContent("");
      setApiPatches([]);
      setApiActions([]);
      setActiveFileId(preview ? codeFiles[0]?.id ?? "" : "");
      return () => { cancelled = true; };
    }
    Promise.all([fetchArtifacts(runId), fetchFiles(runId)])
      .then(([apiArtifacts, files]) => {
        if (cancelled) return;
        setArtifactRows(apiArtifacts.map(artifactFromApi));
        setApiFiles(files);
        setActiveFileId((current) => {
          if (current && files.some((file) => file.path === current)) {
            return current;
          }
          return preferredCodeFile(files)?.path ?? "";
        });
      })
      .catch(() => {
        if (cancelled || preview) return;
        setArtifactRows([]);
        setApiFiles([]);
        setActiveFileId("");
      });
    fetchPatches(runId)
      .then((patches) => { if (!cancelled) setApiPatches(patches as ApiPatch[]); })
      .catch(() => { if (!cancelled && !preview) setApiPatches([]); });
    fetchRunActions(runId)
      .then((actions) => { if (!cancelled) setApiActions(actions); })
      .catch(() => { if (!cancelled && !preview) setApiActions([]); });
    return () => { cancelled = true; };
  }, [preview, refreshToken, runId]);

  useEffect(() => {
    if (preview) {
      setArtifactRows((current) => current.length ? current : mockArtifacts);
      setActiveFileId((current) => current || codeFiles[0]?.id || "");
      return;
    }
    setArtifactRows([]);
    setApiFiles([]);
    setApiFileContent("");
    setApiPatches([]);
    setApiActions([]);
    setActiveFileId("");
  }, [preview, runId]);

  useEffect(() => {
    if (!activeApiFile) {
      if (!preview) setApiFileContent("");
      return;
    }
    let cancelled = false;
    fetchFileContent(runId, activeApiFile.path)
      .then((file) => {
        if (!cancelled) setApiFileContent(file.content);
      })
      .catch(() => {
        if (!cancelled) setApiFileContent("");
      });
    return () => { cancelled = true; };
  }, [activeApiFile, preview, runId]);

  const fileTabs = apiFiles.length
    ? apiFiles.map((file) => ({ id: file.path, label: file.name }))
    : preview ? codeFiles.map((file) => ({
        id: file.id,
        label: file.path.split("/").pop() ?? file.path,
      })) : [];

  const activePatchSyntax = activePatch
    ? patchSyntaxResultFromEvents(events, activePatch.patch_id)
    : undefined;
  const runnerAction =
    apiActions.find((a) => (a.status === "pending" || a.status === "edited")) ??
    apiActions.find((a) => a.execution_status === "running") ??
    apiActions.find((a) => a.tool === "run_command") ??
    apiActions[0];
  const realPatchStatus = activePatch?.status === "applied"
    ? "success"
    : activePatch?.status === "rejected"
      ? "failed"
      : "waiting_review";
  const realRunnerStatus = runnerAction
    ? statusFromActionExecution(runnerAction.execution_status)
    : runnerStatus;
  const realRunnerMessage = runnerAction ? runnerMessageFromAction(runnerAction) : runnerMessage;
  const realRunnerAction = runnerAction ? actionViewFromApi(runnerAction) : approvalRequest;
  const realRunnerReview = runnerAction ? runnerReviewFromAction(runnerAction) : runnerReview;

  return (
    <aside className="inspector" aria-label="Run inspector">
      <div className="inspector-titlebar">
        <strong>Artifacts</strong>
        <StatusPill status={runStatus} />
      </div>

      <div className="tab-list" role="tablist" aria-label="Inspector tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={activeTab === tab.id ? "tab active" : "tab"}
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              type="button"
              title={tab.label}
            >
              <Icon size={15} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      <div className="inspector-content">
        {activeTab === "artifacts" && <ArtifactsPanel artifactRows={artifactRows} />}

        {activeTab === "code" && (
          <CodePanel
            fileTabs={fileTabs}
            activeFileId={activeFileId}
            activeFile={activeFile}
            apiFiles={apiFiles}
            onSelectFile={setActiveFileId}
          />
        )}

        {activeTab === "diff" && (
          activePatch ? (
            <DiffPanel
              patchFile={activePatch.path}
              oldCode={activePatch.old_content}
              newCode={activePatch.new_content}
              patchStatus={realPatchStatus}
              syntaxResult={activePatchSyntax}
              reason={activePatch.reason}
            />
          ) : preview ? (
            <DiffPanel
              patchFile={patchPreview.file}
              oldCode={patchPreview.oldCode}
              newCode={patchPreview.newCode}
              patchStatus={patchStatus}
              onApprove={() => setPatchStatus("success")}
              onReject={() => setPatchStatus("failed")}
              onRevise={() => setPatchStatus("revised")}
            />
          ) : (
            <div className="empty-state">No patch proposal for this run.</div>
          )
        )}

        {activeTab === "runner" && (
          runnerAction ? (
            <RunnerPanel
              approvalRequest={realRunnerAction}
              runnerReview={realRunnerReview}
              runnerStatus={realRunnerStatus}
              runnerMessage={realRunnerMessage}
            />
          ) : preview ? (
            <RunnerPanel
              approvalRequest={approvalRequest}
              runnerReview={runnerReview}
              runnerStatus={runnerStatus}
              runnerMessage={runnerMessage}
              onApprove={() => {
                setRunnerStatus("success");
                setRunnerMessage("Approved. Preview runner recorded a successful bounded smoke test.");
              }}
              onEdit={() => {
                setRunnerStatus("revised");
                setRunnerMessage("Edited command to python main.py --help for a safer first check.");
              }}
              onReject={() => {
                setRunnerStatus("failed");
                setRunnerMessage("Rejected. No command will run until the plan is revised.");
              }}
            />
          ) : (
            <div className="empty-state">No runner action for this run.</div>
          )
        )}

        {activeTab === "tools" && (
          <ToolCallPanel toolCalls={derivedToolCalls.length ? derivedToolCalls : preview ? mockToolCalls : []} />
        )}

      </div>
    </aside>
  );
}

function actionViewFromApi(action: ApiAction): RunnerActionView {
  return {
    id: action.action_id,
    runId: action.run_id,
    agent: action.agent,
    tool: action.tool,
    command: action.edited_command || action.command,
    cwd: action.cwd,
    patchId: action.patch_id,
    path: action.path,
    risk: action.risk,
    reason: action.reason,
    status: action.status,
    executionStatus: action.execution_status,
  };
}

function runnerReviewFromAction(action: ApiAction): RunnerReviewView {
  const result = action.execution_result ?? {};
  const patchResult = isRecord(result.result) ? result.result : result;
  const patchMessage = String(patchResult.message ?? "");
  const command = action.edited_command || action.command;
  const isPatch = action.tool === "apply_patch";
  const stdout = String(result.stdout ?? "");
  const stderr = String(result.stderr ?? "");

  return {
    purpose: isPatch
      ? "Apply a reviewed patch through the backend approval path."
      : "Run a reviewed command through the backend command runner.",
    command: command || action.patch_id || action.path || action.tool,
    risk: action.risk === "blocked" ? "high" : action.risk,
    cwd: action.cwd || ".",
    expectedOutput: isPatch
      ? "Patch result plus syntax check event."
      : "Bounded stdout/stderr and exit code.",
    stdout: isPatch ? patchMessage : stdout,
    stderr,
    exitCode:
      typeof result.exit_code === "number"
        ? result.exit_code
        : null,
  };
}

function patchSyntaxResultFromEvents(
  events: AgentEvent[],
  patchId: string,
): PatchSyntaxResult | undefined {
  const syntaxEvent = [...events]
    .reverse()
    .find((event) => {
      if (
        event.eventType !== "syntax_check_passed" &&
        event.eventType !== "syntax_check_failed"
      ) {
        return false;
      }
      return String(event.payload?.patch_id ?? "") === patchId;
    });
  if (!syntaxEvent) {
    return undefined;
  }
  const failures = Array.isArray(syntaxEvent.payload?.syntax_failures)
    ? syntaxEvent.payload.syntax_failures
        .filter(isRecord)
        .map((failure) => ({
          path: typeof failure.path === "string" ? failure.path : undefined,
          error: typeof failure.error === "string" ? failure.error : undefined,
        }))
    : [];
  return {
    syntaxOk: Boolean(syntaxEvent.payload?.syntax_ok),
    failures,
  };
}

function toolNameFromPayload(payload?: Record<string, unknown>): string {
  if (!payload) {
    return "";
  }
  for (const key of ["tool", "tool_name", "name", "command"]) {
    const value = payload[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return "";
}

function statusFromActionExecution(
  status: ApiAction["execution_status"],
): "waiting_review" | "success" | "failed" | "revised" {
  if (status === "succeeded") return "success";
  if (status === "failed" || status === "blocked") return "failed";
  if (status === "running") return "revised";
  return "waiting_review";
}

function runnerMessageFromAction(action: ApiAction): string {
  if (action.execution_status === "not_started") {
    return action.status === "edited"
      ? "Command edit is saved. Approval is required before execution."
      : "Waiting for approval before execution.";
  }
  if (action.execution_status === "running") {
    return "Execution is in progress.";
  }
  if (action.execution_status === "blocked") {
    return String(
      action.execution_result?.blocked_reason ??
      "Execution was blocked by command policy.",
    );
  }
  if (action.execution_status === "succeeded") {
    return "Execution completed successfully.";
  }
  const stderr = String(action.execution_result?.stderr ?? "");
  return stderr || "Execution completed with a failure result.";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function preferredCodeFile(files: ApiFileNode[]): ApiFileNode | undefined {
  return (
    files.find((file) => file.name.toLowerCase() === "readme.md") ??
    files.find((file) => file.name.toLowerCase() === "main.py") ??
    files.find((file) => file.name.toLowerCase() === "code_agent_manifest.json") ??
    files[0]
  );
}
