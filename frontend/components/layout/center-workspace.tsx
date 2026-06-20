"use client";

import { CheckSquare } from "lucide-react";

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
  return (
    <section className="center-workspace" data-run-status={runStatus}>
      <WorkbenchTabs activeTab={activeTab} onTabChange={onTabChange} />

      {activeTab === "workflow" && (
        <div className="workflow-surface">
          <section className="graph-panel" aria-label="Workflow graph panel">
            <div className="graph-context" title={notice}>
              <span>{mode === "reproduce" ? "Reproduce workflow" : "Product Design workflow"}</span>
              <button className="refresh-link" type="button" onClick={onContinueRun}>Refresh</button>
            </div>
            <WorkflowGraph nodes={graphNodes} />
          </section>
          <ActivityPanel events={timelineEvents} />
        </div>
      )}

      {activeTab === "chat" && (
        <div className="chat-workspace">
        <section className="tool-panel plan-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">Co-planning</p><h2>Editable plan</h2></div>
            <button className="icon-button" title="Approve plan" type="button" onClick={onApprovePlan}><CheckSquare size={17} /></button>
          </div>
          <div className="plan-list">
            {planState.map((step) => (
              <label className="plan-step" key={step.id}>
                <input type="checkbox" checked={step.enabled} onChange={() => onTogglePlanStep(step.id)} />
                <span>{step.label}</span><StatusPill status={step.status} />
              </label>
            ))}
          </div>
        </section>
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
        </div>
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
