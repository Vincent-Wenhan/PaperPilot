"use client";

import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";
import { useState } from "react";

type DiffViewerProps = {
  oldCode: string;
  newCode: string;
  filePath: string;
  patchStatus: "proposed" | "applied" | "rejected";
  onApprove?: () => void;
  onReject?: () => void;
  onRevise?: () => void;
};

const diffStyles = {
  variables: {
    dark: {
      diffViewerBackground: "var(--surface)",
      diffViewerColor: "var(--text)",
      addedBackground: "#1a3a1a",
      addedColor: "#c8e6c9",
      removedBackground: "#3a1a1a",
      removedColor: "#ffcdd2",
      wordAddedBackground: "#2e7d32",
      wordRemovedBackground: "#c62828",
      gutterBackground: "var(--muted)",
      gutterColor: "var(--text-muted)",
    },
  },
};

export function DiffViewer({
  oldCode,
  newCode,
  filePath,
  patchStatus,
  onApprove,
  onReject,
  onRevise,
}: DiffViewerProps) {
  const [viewMode, setViewMode] = useState<"split" | "unified">("split");

  return (
    <div className="diff-viewer">
      <div className="diff-toolbar">
        <span className="diff-path">{filePath}</span>
        <div className="diff-actions">
          <button
            className={`command-button ${viewMode === "split" ? "active" : ""}`}
            type="button"
            onClick={() => setViewMode("split")}
          >
            Split
          </button>
          <button
            className={`command-button ${viewMode === "unified" ? "active" : ""}`}
            type="button"
            onClick={() => setViewMode("unified")}
          >
            Unified
          </button>
        </div>
      </div>
      <div className="diff-content">
        <ReactDiffViewer
          oldValue={oldCode}
          newValue={newCode}
          splitView={viewMode === "split"}
          compareMethod={DiffMethod.WORDS}
          useDarkTheme
          styles={diffStyles}
          leftTitle={`old - ${filePath}`}
          rightTitle={`new - ${filePath}`}
          hideLineNumbers={false}
          showDiffOnly={false}
        />
      </div>
      {patchStatus === "proposed" && (onApprove || onReject || onRevise) && (
        <div className="diff-approval-bar">
          <span>Patch is proposed - review and approve or request revision.</span>
          <div className="action-row">
            {onApprove && (
              <button className="command-button primary" type="button" onClick={onApprove}>
                Approve
              </button>
            )}
            {onRevise && (
              <button className="command-button" type="button" onClick={onRevise}>
                Ask Revision
              </button>
            )}
            {onReject && (
              <button className="command-button" type="button" onClick={onReject}>
                Reject
              </button>
            )}
          </div>
        </div>
      )}
      {patchStatus === "applied" && (
        <div className="diff-status success">Patch applied successfully.</div>
      )}
      {patchStatus === "rejected" && (
        <div className="diff-status rejected">Patch was rejected.</div>
      )}
    </div>
  );
}
