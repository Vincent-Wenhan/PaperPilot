"use client";

import {
  CheckSquare,
  Clock3,
  MessageSquareText,
  Play,
  ShieldCheck,
} from "lucide-react";

import { StatusPill } from "@/components/status-pill";
import type { AgentEvent, PlanStep, RunMode, WorkflowStatus } from "@/lib/mock-data";
import { WorkflowGraph, type GraphNodeData } from "@/components/workflow-graph";

type CenterWorkspaceProps = {
  mode: RunMode;
  notice: string;
  planState: PlanStep[];
  timelineEvents: AgentEvent[];
  chatMessages: Array<{ role: "agent" | "user"; text: string }>;
  approvalStatus: "pending" | "approved" | "edited" | "rejected";
  graphNodes?: GraphNodeData[];
  onTogglePlanStep: (stepId: string) => void;
  onApprovePlan: () => void;
  onAskAgent: () => void;
  onChatInputChange: (value: string) => void;
  chatInput: string;
  onContinueRun: () => void;
  onUpdateApproval: (nextStatus: "approved" | "edited" | "rejected") => void;
};

export function CenterWorkspace({
  mode,
  notice,
  planState,
  timelineEvents,
  chatMessages,
  approvalStatus,
  graphNodes,
  onTogglePlanStep,
  onApprovePlan,
  onAskAgent,
  onChatInputChange,
  chatInput,
  onContinueRun,
  onUpdateApproval,
}: CenterWorkspaceProps) {
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

      <section className="workspace-band two-columns">
        <div className="tool-panel plan-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Co-planning</p>
              <h2>Editable plan</h2>
            </div>
            <button className="icon-button" title="Approve plan" type="button" onClick={onApprovePlan}>
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
        </div>

        <div className="tool-panel chat-panel">
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

      <section className="workspace-band two-columns bottom-band">
        <div className="tool-panel timeline-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Event stream</p>
              <h2>Agent trace</h2>
            </div>
            <Clock3 size={17} />
          </div>
          <div className="timeline">
            {timelineEvents.map((event) => (
              <article className="timeline-event" key={event.id}>
                <div className={`event-dot status-${event.status}`} />
                <div>
                  <span>{event.time}</span>
                  <strong>{event.agent}</strong>
                  <p>{event.message}</p>
                </div>
                <StatusPill status={event.status} />
              </article>
            ))}
          </div>
        </div>

        <div className="tool-panel approval-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Approval</p>
              <h2>Human-in-the-loop</h2>
            </div>
            <ShieldCheck size={18} />
          </div>
          <div className="approval-summary">
            <code>python main.py --smoke-test</code>
            <p>
              Medium-risk generated-code check. Current decision:
              {" "}
              <strong>{approvalStatus}</strong>.
            </p>
          </div>
          <div className="action-row">
            <button className="command-button primary" type="button" onClick={() => onUpdateApproval("approved")}>
              Approve
            </button>
            <button className="command-button" type="button" onClick={() => onUpdateApproval("edited")}>
              Edit
            </button>
            <button className="command-button" type="button" onClick={() => onUpdateApproval("rejected")}>
              Reject
            </button>
          </div>
        </div>
      </section>
    </section>
  );
}

function ChatBubble({ role, text }: { role: "agent" | "user"; text: string }) {
  return <div className={`chat-bubble ${role}`}>{text}</div>;
}
