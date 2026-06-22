"use client";

import { Check } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import { DiffViewer } from "@/components/code/diff-viewer";
import type { PatchSyntaxResult, WorkflowStatus } from "@/lib/workbench-types";

type DiffPanelProps = {
  patchFile: string;
  oldCode: string;
  newCode: string;
  patchStatus: WorkflowStatus;
  syntaxResult?: PatchSyntaxResult;
  reason?: string;
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
  syntaxResult,
  reason,
  onApprove,
  onReject,
  onRevise,
}: DiffPanelProps) {
  const hasSyntaxResult = syntaxResult?.syntaxOk !== undefined;

  return (
    <div className="stack">
      <div className="diff-header">
        <div>
          <p className="eyebrow">Patch proposal</p>
          <strong>{patchFile}</strong>
          {reason && <p>{reason}</p>}
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
      {hasSyntaxResult && (
        <div className={syntaxResult.syntaxOk ? "syntax-result success" : "syntax-result failed"}>
          <strong>
            {syntaxResult.syntaxOk ? "Syntax check passed" : "Syntax check failed"}
          </strong>
          {syntaxResult.failures.length > 0 && (
            <ul>
              {syntaxResult.failures.map((failure, index) => (
                <li key={`${failure.path ?? "failure"}-${index}`}>
                  <code>{failure.path ?? patchFile}</code>
                  <span>{failure.error ?? "Unknown syntax error"}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
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
