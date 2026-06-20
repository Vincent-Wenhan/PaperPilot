"use client";

import { Check, FilePenLine, Shield, X } from "lucide-react";
import type { ReactNode } from "react";

export type PendingAction = {
  id: string;
  runId: string;
  agent: string;
  type:
    | "run_command"
    | "apply_patch"
    | "write_file"
    | "download_resource"
    | "install_dependency"
    | "open_external_url";
  risk: "safe" | "review" | "sandbox" | "blocked";
  reason: string;
  payload: Record<string, unknown>;
  status: "pending" | "approved" | "rejected" | "edited";
};

const RISK_COLORS: Record<string, string> = {
  safe: "var(--green)",
  review: "var(--amber)",
  sandbox: "var(--violet)",
  blocked: "var(--red)",
};

type ApprovalCardProps = {
  action: PendingAction;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEdit: (id: string) => void;
};

export function ApprovalCard({ action, onApprove, onReject, onEdit }: ApprovalCardProps) {
  const isPending = action.status === "pending";
  const command = (action.payload.command as string) ?? (action.payload.path as string) ?? "";

  return (
    <div className={`approval-card risk-${action.risk}`}>
      <div className="approval-card-header">
        <div>
          <span className="eyebrow">{action.type.replace(/_/g, " ")}</span>
          <strong>{action.agent}</strong>
        </div>
        <span
          className="risk-badge"
          style={{ color: RISK_COLORS[action.risk] ?? "var(--text-muted)" }}
        >
          <Shield size={13} />
          {action.risk}
        </span>
      </div>
      {command && (
        <pre className="approval-command">
          <code>{command}</code>
        </pre>
      )}
      <p className="approval-reason">{action.reason}</p>
      {isPending && (
        <div className="action-row" style={{ marginTop: 8 }}>
          <button
            className="command-button primary"
            type="button"
            onClick={() => onApprove(action.id)}
          >
            Approve
          </button>
          <button
            className="command-button"
            type="button"
            onClick={() => onEdit(action.id)}
          >
            Edit
          </button>
          <button
            className="command-button"
            type="button"
            onClick={() => onReject(action.id)}
          >
            Reject
          </button>
        </div>
      )}
      {!isPending && (
        <div className="approval-status" style={{ marginTop: 8 }}>
          <strong>{action.status}</strong>
        </div>
      )}
    </div>
  );
}

type ActionApprovalDrawerProps = {
  open: boolean;
  actions: PendingAction[];
  onClose: () => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEdit: (id: string) => void;
  children?: ReactNode;
};

export function ActionApprovalDrawer({
  open,
  actions,
  onClose,
  onApprove,
  onReject,
  onEdit,
  children,
}: ActionApprovalDrawerProps) {
  if (!open) return null;

  const action = actions.find((item) => item.status === "pending") ?? actions[0];
  if (!action) return null;
  const command = (action.payload.command as string) ?? (action.payload.path as string) ?? "Review requested action";

  return (
    <aside className="approval-overlay" role="complementary" aria-label="Approval Required">
      <header className="approval-overlay-header">
        <span className="approval-alert"><Shield size={17} /></span>
        <strong>Approval Required</strong>
        <button className="icon-button" type="button" onClick={onClose} title="Close approval">
          <X size={16} />
        </button>
      </header>
      <p>The agent wants to apply the following action:</p>
      <div className="approval-command-block">
        <code>{command}</code>
        <span>{action.type.replace(/_/g, " ")}</span>
      </div>
      <div className="approval-reason-block">
        <span>Reason</span>
        <p>{action.reason}</p>
      </div>
      {action.status === "pending" && (
        <div className="approval-actions">
          <button className="command-button primary" type="button" onClick={() => onApprove(action.id)}>
            <Check size={15} /> Approve
          </button>
          <button className="command-button" type="button" onClick={() => onEdit(action.id)}>
            <FilePenLine size={15} /> Edit
          </button>
          <button className="command-button reject" type="button" onClick={() => onReject(action.id)}>
            <X size={15} /> Reject
          </button>
        </div>
      )}
      {children}
    </aside>
  );
}
