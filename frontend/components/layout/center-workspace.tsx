"use client";

import {
  CheckSquare,
  MessageSquareText,
  Play,
  ShieldCheck,
} from "lucide-react";

import { StatusPill } from "@/components/status-pill";
import type { AgentEvent, PlanStep, RunMode, WorkflowStatus } from "@/lib/mock-data";
import type { EvaluationIssue } from "@/components/productize/evaluation-issues";
import { IssueCard } from "@/components/productize/evaluation-issues";
import { WorkflowGraph, type GraphNodeData } from "@/components/workflow-graph";
import { WorkbenchTabs, type WorkbenchTabId } from "@/components/workbench/workbench-tabs";
import { ActivityPanel } from "@/components/workbench/activity-panel";

type CenterWorkspaceProps = {
  mode: RunMode;
  notice: string;
  planState: PlanStep[];
  timelineEvents: AgentEvent[];
  chatMessages: Array<{ role: "agent" | "user"; text: string }>;
  runStatus: WorkflowStatus;
  graphNodes?: GraphNodeData[];
  activeTab: WorkbenchTabId;
  onTabChange: (tab: WorkbenchTabId) => void;
  onTogglePlanStep: (stepId: string) => void;
  onApprovePlan: () => void;
  onAskAgent: () => void;
  onChatInputChange: (value: string) => void;
  chatInput: string;
  onContinueRun: () => void;
  evaluationIssues?: EvaluationIssue[];
  onReduceScope?: (id: string) => void;
  onRevisePrd?: (id: string) => void;
  onRevisePrototype?: (id: string) => void;
  onAcceptWarning?: (id: string) => void;
};

export function CenterWorkspace({
  mode,
  notice,
  planState,
  timelineEvents,
  chatMessages,
  runStatus,
  graphNodes,
  activeTab,
  onTabChange,
  onTogglePlanStep,
  onApprovePlan,
  onAskAgent,
  onChatInputChange,
  chatInput,
  onContinueRun,
  evaluationIssues,
  onReduceScope,
  onRevisePrd,
  onRevisePrototype,
  onAcceptWarning,
}: CenterWorkspaceProps) {
  const approvalCopy = getApprovalCopy(runStatus);
  return (
    <section className="center-workspace">
      <div className="workspace-toolbar">
        <div>
          <p className="eyebrow">Run</p>
          <h2>{mode === "reproduce" ? "Reproduce workflow" : "Productize workflow"}</h2>
        </div>
        <div className="toolbar-actions">
          <button className="command-button" type="button" onClick={onAskAgent}>
            <MessageSquareText size={15} />
            Ask Agent
          </button>
          <button className="command-button primary" type="button" onClick={onContinueRun}>
            <Play size={15} />
            Refresh
          </button>
        </div>
      </div>

      <div className="notice-strip">{notice}</div>

      <WorkbenchTabs activeTab={activeTab} onTabChange={onTabChange} />

      {activeTab === "workflow" && (
        <>
          <section className="tool-panel plan-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Co-planning</p>
                <h2>Editable plan</h2>
              </div>
              <button
                className="icon-button"
                title="Approve plan"
                type="button"
                onClick={onApprovePlan}
              >
                <CheckSquare size={17} />
              </button>
            </div>
            <div className="plan-list">
              {planState.map((step) => (
                <label className="plan-step" key={step.id}>
                  <input
                    type="checkbox"
                    checked={step.enabled}
                    onChange={() => onTogglePlanStep(step.id)}
                  />
                  <span>{step.label}</span>
                  <StatusPill status={step.status} />
                </label>
              ))}
            </div>
          </section>

          <section className="tool-panel graph-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">LangGraph</p>
                <h2>Workflow graph</h2>
              </div>
              <div className="legend">
                <span className="legend-item success">success</span>
                <span className="legend-item running">running</span>
                <span className="legend-item review">review</span>
              </div>
            </div>
            <WorkflowGraph nodes={graphNodes} />
          </section>

          <ActivityPanel events={timelineEvents} />

          <section className="tool-panel approval-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Approval</p>
                <h2>Human-in-the-loop</h2>
              </div>
              <ShieldCheck size={18} />
            </div>
            <div className="approval-summary">
              <code>{approvalCopy.command}</code>
              <p>{approvalCopy.message}</p>
            </div>
          </section>
        </>
      )}

      {activeTab === "chat" && (
        <section className="tool-panel chat-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Agent chat</p>
              <h2>Artifact-aware context</h2>
            </div>
            <StatusPill status="running" />
          </div>
          <div className="chat-thread">
            {chatMessages.map((message, index) => (
              <ChatBubble
                key={`${message.role}-${index}`}
                role={message.role}
                text={message.text}
              />
            ))}
          </div>
          <div className="composer">
            <span>@</span>
            <input
              aria-label="Agent message"
              placeholder="paper, repo, prd, code, terminal"
              value={chatInput}
              onChange={(event) => onChatInputChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  onAskAgent();
                }
              }}
            />
          </div>
        </section>
      )}

      {activeTab === "evaluation" && (
        <section className="tool-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Quality</p>
              <h2>Evaluation issues</h2>
            </div>
          </div>
          {evaluationIssues && evaluationIssues.length > 0 ? (
            <div className="stack">
              {evaluationIssues.map((issue) => (
                <IssueCard
                  key={issue.id}
                  issue={issue}
                  onReduceScope={onReduceScope}
                  onRevisePrd={onRevisePrd}
                  onRevisePrototype={onRevisePrototype}
                  onAcceptWarning={onAcceptWarning}
                />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              No evaluation issues. Run a productize pipeline to see evaluator feedback.
            </div>
          )}
        </section>
      )}

      {activeTab === "product" && (
        <section className="tool-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Product Design</p>
              <h2>PRD / MVP / Prototype</h2>
            </div>
          </div>
          <div className="empty-state">
            Product design content will appear after running a productize pipeline. Check the
            Artifacts and Code tabs in the Inspector for generated outputs.
          </div>
        </section>
      )}
    </section>
  );
}

function ChatBubble({ role, text }: { role: "agent" | "user"; text: string }) {
  return <div className={`chat-bubble ${role}`}>{text}</div>;
}

function getApprovalCopy(runStatus: WorkflowStatus) {
  if (runStatus === "running") {
    return {
      command: "waiting for backend agent stage",
      message:
        "No command approval is pending. The backend agent is still running; artifacts appear after the pipeline finishes.",
    };
  }
  if (runStatus === "waiting_review") {
    return {
      command: "review generated report and code",
      message:
        "The run finished with review items. Open Artifacts, Logs, or Code to inspect the generated output.",
    };
  }
  if (runStatus === "success") {
    return {
      command: "pipeline complete",
      message: "The run completed successfully. Generated artifacts are available in the inspector.",
    };
  }
  if (runStatus === "failed") {
    return {
      command: "pipeline failed",
      message: "The run failed. Open Logs to inspect the backend error before retrying.",
    };
  }
  return {
    command: "no active backend approval",
    message: "Create a backend run to receive live approval requests.",
  };
}
