"use client";

import { Check } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import { DiffViewer } from "@/components/code/diff-viewer";
import type { WorkflowStatus } from "@/lib/mock-data";

type DiffPanelProps = {
  patchFile: string;
  oldCode: string;
  newCode: string;
  patchStatus: WorkflowStatus;
  onApprove?: () => void;
  onReject?: () => void;
  onRevise?: () => void;
};

function statusToStep(s: WorkflowStatus): "proposed" | "applied" | "rejected" {
  if (s === "success" || s === "revised") return "applied";
  if (s === "failed") return "rejected";
  return "proposed";
}

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
      <DiffViewer
        oldCode={oldCode}
        newCode={newCode}
        filePath={patchFile}
        patchStatus={statusToStep(patchStatus)}
        onApprove={onApprove}
        onReject={onReject}
        onRevise={onRevise}
      />
      {patchStatus !== "success" && patchStatus !== "failed" && (onApprove || onReject || onRevise) && (
        <div className="action-row">
          {onApprove && (
            <button className="command-button primary" type="button" onClick={onApprove}>
              <Check size={15} />
              Approve Patch
            </button>
          )}
          {onReject && (
            <button className="command-button" type="button" onClick={onReject}>
              Reject
            </button>
          )}
          {onRevise && (
            <button className="command-button" type="button" onClick={onRevise}>
              Ask Revision
            </button>
          )}
        </div>
      )}
    </div>
  );
}
