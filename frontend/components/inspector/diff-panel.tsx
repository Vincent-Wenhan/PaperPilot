"use client";

import { Check } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/mock-data";

type DiffPanelProps = {
  patchFile: string;
  oldCode: string;
  newCode: string;
  patchStatus: WorkflowStatus;
  onApprove: () => void;
  onReject: () => void;
  onRevise: () => void;
};

export function DiffPanel({
  patchFile,
  oldCode,
  newCode,
  patchStatus,
  onApprove,
  onReject,
  onRevise,
}: DiffPanelProps) {
  return (
    <div className="stack">
      <div className="diff-header">
        <div>
          <p className="eyebrow">Patch proposal</p>
          <strong>{patchFile}</strong>
        </div>
        <StatusPill status={patchStatus} />
      </div>
      <div className="diff-grid">
        <pre className="diff-pane old">
          <code>{oldCode}</code>
        </pre>
        <pre className="diff-pane new">
          <code>{newCode}</code>
        </pre>
      </div>
      <div className="action-row">
        <button className="command-button primary" type="button" onClick={onApprove}>
          <Check size={15} />
          Approve Patch
        </button>
        <button className="command-button" type="button" onClick={onReject}>
          Reject
        </button>
        <button className="command-button" type="button" onClick={onRevise}>
          Ask Revision
        </button>
      </div>
    </div>
  );
}
