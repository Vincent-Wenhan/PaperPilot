"use client";

import { Check } from "lucide-react";
import type {
  RunnerActionView,
  RunnerReviewView,
  WorkflowStatus,
} from "@/lib/workbench-types";

type RunnerPanelProps = {
  approvalRequest: RunnerActionView;
  runnerReview: RunnerReviewView;
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
  const executionLines = [
    runnerMessage,
    runnerReview.stdout ? `stdout:\n${runnerReview.stdout}` : "",
    runnerReview.stderr ? `stderr:\n${runnerReview.stderr}` : "",
  ].filter(Boolean);

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
            <dd>
              <code>
                {approvalRequest.command ||
                  approvalRequest.patchId ||
                  approvalRequest.path ||
                  "No command payload"}
              </code>
            </dd>
          </div>
          {approvalRequest.path && (
            <div>
              <dt>Path</dt>
              <dd><code>{approvalRequest.path}</code></dd>
            </div>
          )}
          {approvalRequest.patchId && (
            <div>
              <dt>Patch</dt>
              <dd><code>{approvalRequest.patchId}</code></dd>
            </div>
          )}
          {approvalRequest.cwd && (
            <div>
              <dt>Working dir</dt>
              <dd><code>{approvalRequest.cwd}</code></dd>
            </div>
          )}
          {approvalRequest.status && (
            <div>
              <dt>Status</dt>
              <dd>{approvalRequest.status}</dd>
            </div>
          )}
          {approvalRequest.executionStatus && (
            <div>
              <dt>Execution</dt>
              <dd>{approvalRequest.executionStatus}</dd>
            </div>
          )}
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
        <strong>{runnerReview.exitCode ?? (runnerStatus === "success" ? 0 : "not run")}</strong>
      </div>
      <pre className="terminal-block">
        <code>{executionLines.join("\n\n")}</code>
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
