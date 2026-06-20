"use client";

import { Check } from "lucide-react";
import type { ApprovalRequest, RunnerReview, WorkflowStatus } from "@/lib/mock-data";

type RunnerPanelProps = {
  approvalRequest: ApprovalRequest;
  runnerReview: RunnerReview;
  runnerStatus: WorkflowStatus;
  runnerMessage: string;
  onApprove?: () => void;
  onEdit?: () => void;
  onReject?: () => void;
};

export function RunnerPanel({
  approvalRequest,
  runnerReview,
  runnerStatus,
  runnerMessage,
  onApprove,
  onEdit,
  onReject,
}: RunnerPanelProps) {
  return (
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
            <dd><code>{approvalRequest.command}</code></dd>
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
      {(onApprove || onEdit || onReject) && (
        <div className="action-row">
          {onApprove && (
            <button className="command-button primary" type="button" onClick={onApprove}>
              <Check size={15} /> Approve
            </button>
          )}
          {onEdit && <button className="command-button" type="button" onClick={onEdit}>Edit</button>}
          {onReject && <button className="command-button" type="button" onClick={onReject}>Reject</button>}
        </div>
      )}
    </div>
  );
}
