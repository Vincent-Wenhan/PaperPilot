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
  type AgentEvent,
  approvalRequest,
  artifacts as mockArtifacts,
  codeFiles,
  patchPreview,
  runnerReview,
  toolCalls as mockToolCalls,
  type ToolCall,
} from "@/lib/mock-data";
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
  const [derivedToolCalls, setDerivedToolCalls] = useState<ToolCall[]>([]);
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
    const calls: ToolCall[] = events
      .filter((e) => e.eventType === "tool_call" || e.eventType === "tool_result")
      .map((e) => ({
        id: e.id,
        action: e.eventType === "tool_call" ? e.message : "",
        observation: e.eventType === "tool_result" ? e.message : "",
        status: e.status,
      }));
    // Merge paired tool_call/tool_result events
    const merged: ToolCall[] = [];
    const byPrefix = new Map<string, ToolCall>();
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

  const runnerAction =
    apiActions.find((a) => a.tool === "run_command" && (a.status === "pending" || a.status === "edited")) ??
    apiActions.find((a) => a.tool === "run_command");
  const realPatchStatus = activePatch?.status === "applied"
    ? "success"
    : activePatch?.status === "rejected"
      ? "failed"
      : "waiting_review";
  const realRunnerStatus = runnerAction
    ? statusFromActionExecution(runnerAction.execution_status)
    : runnerStatus;
  const realRunnerMessage = runnerAction
    ? runnerMessageFromAction(runnerAction)
    : runnerMessage;

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
              approvalRequest={{
                id: runnerAction.action_id,
                agent: runnerAction.agent,
                tool: runnerAction.tool,
                command: runnerAction.edited_command || runnerAction.command,
                risk: runnerAction.risk,
                reason: runnerAction.reason,
              }}
              runnerReview={{
                ...runnerReview,
                command: runnerAction.edited_command || runnerAction.command,
                risk: runnerAction.risk === "blocked" ? "high" : runnerAction.risk,
                cwd: runnerAction.cwd,
                stdout: String(runnerAction.execution_result?.stdout ?? ""),
                stderr: String(runnerAction.execution_result?.stderr ?? ""),
                exitCode: typeof runnerAction.execution_result?.exit_code === "number"
                  ? runnerAction.execution_result.exit_code
                  : null,
              }}
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

function preferredCodeFile(files: ApiFileNode[]): ApiFileNode | undefined {
  return (
    files.find((file) => file.name.toLowerCase() === "readme.md") ??
    files.find((file) => file.name.toLowerCase() === "main.py") ??
    files.find((file) => file.name.toLowerCase() === "code_agent_manifest.json") ??
    files[0]
  );
}
