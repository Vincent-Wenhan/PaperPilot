"use client";

import { Check, FilePenLine, Shield, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

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
  executionStatus?: "not_started" | "running" | "succeeded" | "failed" | "blocked";
};

type PendingActionPayload = {
  command?: string;
  patchId?: string;
  files?: string[];
  cwd?: string;
  expectedEffect?: string;
  riskReason?: string;
  path?: string;
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
  onEdit: (id: string, command: string) => void;
  busy?: boolean;
};

export function ApprovalCard({ action, onApprove, onReject, onEdit, busy = false }: ApprovalCardProps) {
  const isPending = action.status === "pending" || action.status === "edited";
  const payload = action.payload as PendingActionPayload;
  const command = payload.command ?? payload.path ?? "";

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
      <ApprovalRiskDetails action={action} />
      {isPending && (
        <div className="action-row" style={{ marginTop: 8 }}>
          <button
            className="command-button primary"
            type="button"
            onClick={() => onApprove(action.id)}
            disabled={busy}
          >
            Approve & Execute
          </button>
          <button
            className="command-button"
            type="button"
            onClick={() => onEdit(action.id, command)}
            disabled={busy || action.type !== "run_command"}
          >
            Edit
          </button>
          <button
            className="command-button"
            type="button"
            onClick={() => onReject(action.id)}
            disabled={busy}
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
  onEdit: (id: string, command: string) => void;
  busyActionId?: string;
  children?: ReactNode;
};

export function ActionApprovalDrawer({
  open,
  actions,
  onClose,
  onApprove,
  onReject,
  onEdit,
  busyActionId = "",
  children,
}: ActionApprovalDrawerProps) {
  const [editing, setEditing] = useState(false);
  const [draftCommand, setDraftCommand] = useState("");
  const action =
    actions.find((item) => item.status === "pending" || item.status === "edited") ??
    actions[0];
  const command =
    ((action?.payload.command as string | undefined) ??
    (action?.payload.path as string | undefined) ??
    "Review requested action");

  useEffect(() => {
    setEditing(false);
    setDraftCommand(String(command));
  }, [action?.id, command]);

  if (!open || !action) return null;

  const isBusy = busyActionId === action.id || action.executionStatus === "running";
  const canAct = action.status === "pending" || action.status === "edited";
  const payload = action.payload as PendingActionPayload;

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
      <div className="approval-reason-block">
        <span>Files affected</span>
        <p>{formatFiles(payload)}</p>
      </div>
      <div className="approval-reason-block">
        <span>Risk reason</span>
        <p>{payload.riskReason || action.reason || "Review required before execution."}</p>
      </div>
      <div className="approval-reason-block">
        <span>Expected effect</span>
        <p>{payload.expectedEffect || expectedEffectFor(action)}</p>
      </div>
      {editing && action.type === "run_command" && (
        <div className="approval-edit-block">
          <label htmlFor="approval-command-edit">Command</label>
          <textarea
            id="approval-command-edit"
            value={draftCommand}
            onChange={(event) => setDraftCommand(event.target.value)}
            rows={4}
          />
          <div className="action-row">
            <button
              className="command-button primary"
              disabled={isBusy || !draftCommand.trim()}
              type="button"
              onClick={() => {
                onEdit(action.id, draftCommand);
                setEditing(false);
              }}
            >
              Save Edit
            </button>
            <button
              className="command-button"
              disabled={isBusy}
              type="button"
              onClick={() => {
                setDraftCommand(String(command));
                setEditing(false);
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      {canAct && !editing && (
        <div className="approval-actions">
          <button
            className="command-button primary"
            disabled={isBusy}
            type="button"
            onClick={() => onApprove(action.id)}
          >
            <Check size={15} /> {isBusy ? "Executing" : "Approve & Execute"}
          </button>
          <button
            className="command-button"
            disabled={isBusy || action.type !== "run_command"}
            type="button"
            onClick={() => {
              setDraftCommand(String(command));
              setEditing(true);
            }}
          >
            <FilePenLine size={15} /> Edit
          </button>
          <button
            className="command-button reject"
            disabled={isBusy}
            type="button"
            onClick={() => onReject(action.id)}
          >
            <X size={15} /> Reject
          </button>
        </div>
      )}
      {children}
    </aside>
  );
}

function ApprovalRiskDetails({ action }: { action: PendingAction }) {
  const payload = action.payload as PendingActionPayload;
  return (
    <div className="approval-risk-details">
      <p className="approval-reason">{action.reason}</p>
      <dl>
        <dt>Files</dt>
        <dd>{formatFiles(payload)}</dd>
        <dt>Risk</dt>
        <dd>{payload.riskReason || action.reason || "Review required before execution."}</dd>
        <dt>Effect</dt>
        <dd>{payload.expectedEffect || expectedEffectFor(action)}</dd>
      </dl>
    </div>
  );
}

function formatFiles(payload: PendingActionPayload): string {
  if (payload.files && payload.files.length > 0) return payload.files.join(", ");
  if (payload.path) return payload.path;
  if (payload.patchId) return `Patch ${payload.patchId}`;
  return "No files declared";
}

function expectedEffectFor(action: PendingAction): string {
  if (action.type === "apply_patch") return "Apply a proposed patch to the workspace.";
  if (action.type === "run_command") return "Run the command in the configured workspace.";
  if (action.type === "write_file") return "Write or update a generated artifact.";
  if (action.type === "install_dependency") return "Install a project dependency.";
  if (action.type === "download_resource") return "Download an external resource into the run workspace.";
  return "Open an external URL for review.";
}
