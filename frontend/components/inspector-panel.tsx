"use client";

import {
  Check,
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
  refreshToken = "",
  runId,
  runStatus = "pending",
}: {
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
        if (cancelled) {
          return;
        }
        setArtifactRows(apiArtifacts.map(artifactFromApi));
        setApiFiles(files);
        if (files[0]?.path) {
          setActiveFileId(files[0].path);
        }
      })
      .catch(() => {
        // Preserve mock inspector data when the FastAPI server is unavailable.
      });
    return () => {
      cancelled = true;
    };
  }, [refreshToken, runId]);

  useEffect(() => {
    if (!activeApiFile) {
      return;
    }
    let cancelled = false;
    fetchFileContent(runId, activeApiFile.path)
      .then((file) => {
        if (!cancelled) {
          setApiFileContent(file.content);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setApiFileContent("");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeApiFile, runId]);

  const fileTabs = apiFiles.length
    ? apiFiles.map((file) => ({
        id: file.path,
        label: file.name,
      }))
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
        {activeTab === "artifacts" && (
          <div className="stack">
            {artifactRows.map((artifact) => (
              <div className="artifact-row" key={artifact.id}>
                <div>
                  <strong>{artifact.name}</strong>
                  <span>{artifact.kind}</span>
                  <code>{artifact.path}</code>
                </div>
                <StatusPill status={artifact.status} />
              </div>
            ))}
          </div>
        )}

        {activeTab === "code" && activeFile && (
          <div className="code-tab">
            <div className="file-tabs">
              {fileTabs.map((file) => (
                <button
                  key={file.id}
                  className={activeFileId === file.id ? "file-tab active" : "file-tab"}
                  onClick={() => setActiveFileId(file.id)}
                  type="button"
                >
                  {file.label}
                </button>
              ))}
            </div>
            <div className="code-meta">
              <span>{activeFile.path}</span>
              <span>{activeFile.language}</span>
            </div>
            <pre className="code-block">
              <code>{activeFile.content}</code>
            </pre>
          </div>
        )}

        {activeTab === "diff" && (
          <div className="stack">
            <div className="diff-header">
              <div>
                <p className="eyebrow">Patch proposal</p>
                <strong>{patchPreview.file}</strong>
              </div>
              <StatusPill status={patchStatus} />
            </div>
            <div className="diff-grid">
              <pre className="diff-pane old">
                <code>{patchPreview.oldCode}</code>
              </pre>
              <pre className="diff-pane new">
                <code>{patchPreview.newCode}</code>
              </pre>
            </div>
            <div className="action-row">
              <button
                className="command-button primary"
                type="button"
                onClick={() => setPatchStatus("success")}
              >
                <Check size={15} />
                Approve Patch
              </button>
              <button
                className="command-button"
                type="button"
                onClick={() => setPatchStatus("failed")}
              >
                Reject
              </button>
              <button
                className="command-button"
                type="button"
                onClick={() => setPatchStatus("revised")}
              >
                Ask Revision
              </button>
            </div>
          </div>
        )}

        {activeTab === "runner" && (
          <div className="stack">
            <div className="action-request">
              <p className="eyebrow">Action request</p>
              <h3>{approvalRequest.tool}</h3>
              <dl>
                <div>
                  <dt>Agent</dt>
                  <dd>{approvalRequest.agent}</dd>
                </div>
                <div>
                  <dt>Command</dt>
                  <dd>
                    <code>{approvalRequest.command}</code>
                  </dd>
                </div>
                <div>
                  <dt>Risk</dt>
                  <dd>{approvalRequest.risk}</dd>
                </div>
                <div>
                  <dt>Reason</dt>
                  <dd>{approvalRequest.reason}</dd>
                </div>
              </dl>
            </div>
            <div className="runner-grid">
              <span>Purpose</span>
              <strong>{runnerReview.purpose}</strong>
              <span>Working dir</span>
              <code>{runnerReview.cwd}</code>
              <span>Expected</span>
              <strong>{runnerReview.expectedOutput}</strong>
              <span>Exit code</span>
              <strong>{runnerStatus === "success" ? 0 : runnerReview.exitCode ?? "not run"}</strong>
            </div>
            <pre className="terminal-block">
              <code>{runnerMessage}</code>
            </pre>
            <div className="action-row">
              <button
                className="command-button primary"
                type="button"
                onClick={() => {
                  setRunnerStatus("success");
                  setRunnerMessage("Approved. Preview runner recorded a successful bounded smoke test.");
                }}
              >
                <Check size={15} />
                Approve
              </button>
              <button
                className="command-button"
                type="button"
                onClick={() => {
                  setRunnerStatus("revised");
                  setRunnerMessage("Edited command to python main.py --help for a safer first check.");
                }}
              >
                Edit
              </button>
              <button
                className="command-button"
                type="button"
                onClick={() => {
                  setRunnerStatus("failed");
                  setRunnerMessage("Rejected. No command will run until the plan is revised.");
                }}
              >
                Reject
              </button>
            </div>
          </div>
        )}

        {activeTab === "tools" && (
          <div className="stack">
            {toolCalls.map((call) => (
              <div className="tool-call" key={call.id}>
                <div>
                  <code>{call.action}</code>
                  <p>{call.observation}</p>
                </div>
                <StatusPill status={call.status} />
              </div>
            ))}
          </div>
        )}

        {activeTab === "logs" && (
          <pre className="terminal-block">
            <code>
              {"> node_started repository_understanding\n> tool_call code_search argparse\n> human_review_required run_command\n> waiting_for_user action act_001\n"}
            </code>
          </pre>
        )}

        {activeTab === "preview" && (
          <div className="preview-frame">
            <div className="preview-toolbar">
              <span />
              <span />
              <span />
            </div>
            <div className="preview-body">
              <p className="eyebrow">Generated Product</p>
              <h3>Mock-first analysis console</h3>
              <div className="preview-metric">
                <span>Demo readiness</span>
                <strong>4.2 / 5</strong>
              </div>
              <div className="preview-metric">
                <span>Adapter mode</span>
                <strong>Mock</strong>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
