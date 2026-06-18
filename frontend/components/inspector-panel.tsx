"use client";

import {
  Code2,
  FileText,
  GitCompare,
  ListChecks,
  Play,
  RotateCcw,
  Terminal,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  type AgentEvent,
  approvalRequest,
  artifacts,
  codeFiles,
  patchPreview,
  runnerReview,
  toolCalls,
} from "@/lib/mock-data";
import { StatusPill } from "@/components/status-pill";
import {
  artifactFromApi,
  fetchArtifacts,
  fetchFileContent,
  fetchFiles,
  type ApiFileNode,
} from "@/lib/api";
import { ArtifactsPanel } from "@/components/inspector/artifacts-panel";
import { CodePanel } from "@/components/inspector/code-panel";
import { DiffPanel } from "@/components/inspector/diff-panel";
import { RunnerPanel } from "@/components/inspector/runner-panel";
import { ToolCallPanel } from "@/components/inspector/tool-call-panel";
import { LogsPanel } from "@/components/inspector/logs-panel";
import { PreviewPanel } from "@/components/inspector/preview-panel";

type InspectorTab = "artifacts" | "code" | "diff" | "runner" | "tools" | "logs" | "preview";

const tabs: Array<{ id: InspectorTab; label: string; icon: LucideIcon }> = [
  { id: "artifacts", label: "Artifacts", icon: FileText },
  { id: "code", label: "Code", icon: Code2 },
  { id: "diff", label: "Diff", icon: GitCompare },
  { id: "runner", label: "Runner", icon: Terminal },
  { id: "tools", label: "Tool Calls", icon: ListChecks },
  { id: "logs", label: "Logs", icon: Play },
  { id: "preview", label: "Preview", icon: RotateCcw },
];

export function InspectorPanel({
  events = [],
  refreshToken = "",
  runId,
  runStatus = "pending",
}: {
  events?: AgentEvent[];
  refreshToken?: string;
  runId: string;
  runStatus?: "pending" | "running" | "success" | "waiting_review" | "failed" | "revised";
}) {
  const [activeTab, setActiveTab] = useState<InspectorTab>("artifacts");
  const [activeFileId, setActiveFileId] = useState(codeFiles[0]?.id ?? "");
  const [artifactRows, setArtifactRows] = useState(artifacts);
  const [apiFiles, setApiFiles] = useState<ApiFileNode[]>([]);
  const [apiFileContent, setApiFileContent] = useState("");
  const [patchStatus, setPatchStatus] = useState<
    "waiting_review" | "success" | "failed" | "revised"
  >("waiting_review");
  const [runnerStatus, setRunnerStatus] = useState<
    "waiting_review" | "success" | "failed" | "revised"
  >("waiting_review");
  const [runnerMessage, setRunnerMessage] = useState(runnerReview.diagnosis);

  const activeMockFile =
    codeFiles.find((file) => file.id === activeFileId) ?? codeFiles[0];
  const activeApiFile = apiFiles.find((file) => file.path === activeFileId);
  const activeFile = activeApiFile
    ? {
        id: activeApiFile.path,
        path: activeApiFile.path,
        language: activeApiFile.path.endsWith(".py") ? "python" : "text",
        content: apiFileContent,
      }
    : activeMockFile;

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchArtifacts(runId), fetchFiles(runId)])
      .then(([apiArtifacts, files]) => {
        if (cancelled) return;
        setArtifactRows(apiArtifacts.map(artifactFromApi));
        setApiFiles(files);
        if (files[0]?.path) setActiveFileId(files[0].path);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [refreshToken, runId]);

  useEffect(() => {
    if (!activeApiFile) return;
    let cancelled = false;
    fetchFileContent(runId, activeApiFile.path)
      .then((file) => {
        if (!cancelled) setApiFileContent(file.content);
      })
      .catch(() => {
        if (!cancelled) setApiFileContent("");
      });
    return () => { cancelled = true; };
  }, [activeApiFile, runId]);

  const fileTabs = apiFiles.length
    ? apiFiles.map((file) => ({ id: file.path, label: file.name }))
    : codeFiles.map((file) => ({
        id: file.id,
        label: file.path.split("/").pop() ?? file.path,
      }));

  return (
    <aside className="inspector">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Inspector</p>
          <h2>Run workspace</h2>
        </div>
        <StatusPill status={runStatus} />
      </div>

      <div className="tab-list" role="tablist" aria-label="Inspector tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={activeTab === tab.id ? "tab active" : "tab"}
              onClick={() => setActiveTab(tab.id)}
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
          <DiffPanel
            patchFile={patchPreview.file}
            oldCode={patchPreview.oldCode}
            newCode={patchPreview.newCode}
            patchStatus={patchStatus}
            onApprove={() => setPatchStatus("success")}
            onReject={() => setPatchStatus("failed")}
            onRevise={() => setPatchStatus("revised")}
          />
        )}

        {activeTab === "runner" && (
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
        )}

        {activeTab === "tools" && <ToolCallPanel toolCalls={toolCalls} />}

        {activeTab === "logs" && <LogsPanel events={events} />}

        {activeTab === "preview" && <PreviewPanel />}
      </div>
    </aside>
  );
}
