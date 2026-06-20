"use client";

import { Layers } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/mock-data";

export type TopBarRunState = {
  projectName: string;
  runId?: string;
  mode: "reproduce" | "productize";
  status: WorkflowStatus;
  elapsed?: string;
  model?: string;
};

type TopBarProps = {
  run: TopBarRunState;
  onNewRun: () => void;
  onModeChange?: (mode: "reproduce" | "productize") => void;
};

export function TopBar({ run, onNewRun, onModeChange }: TopBarProps) {
  const initials = run.projectName
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");

  return (
    <header className="topbar">
      <div className="brand-block">
        <div className="brand-mark">
          <Layers size={18} />
        </div>
        <div>
          <span className="brand-name">PaperPilot</span>
          <span className="brand-subtitle">Research Agent IDE</span>
        </div>
      </div>

      <div className="breadcrumbs">
        <span>Projects</span>
        <span className="breadcrumb-sep">/</span>
        <strong>{run.projectName}</strong>
      </div>

      <select
        className="mode-select"
        value={run.mode}
        onChange={(event) =>
          onModeChange?.(event.target.value as "reproduce" | "productize")
        }
      >
        <option value="reproduce">Reproduce</option>
        <option value="productize">Product Design</option>
      </select>

      <div className="run-status">
        <span>{run.runId ?? "No Run"}</span>
        <StatusPill status={run.status} />
        <span>{run.elapsed ?? "00:00:00"}</span>
      </div>

      <button className="command-button primary" type="button" onClick={onNewRun}>
        New Run
      </button>

      <div className="avatar">{initials || "PP"}</div>
    </header>
  );
}
