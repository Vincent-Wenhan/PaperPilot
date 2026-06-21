"use client";

import { ChevronDown, ChevronRight, Play } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/workbench-types";

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
  return (
    <header className="topbar" aria-label="Project context">
      <div className="breadcrumbs">
        <span>Projects</span>
        <ChevronRight size={15} />
        <strong>{run.projectName}</strong>
        <ChevronDown size={15} />
      </div>

      <label className="mode-control">
        <span>Mode:</span>
        <select
          className="mode-select"
          aria-label="Workbench mode"
          value={run.mode}
          onChange={(event) => onModeChange?.(event.target.value as "reproduce" | "productize")}
        >
          <option value="reproduce">Reproduce</option>
          <option value="productize">Product Design</option>
        </select>
      </label>

      <div className="topbar-spacer" />

      <div className="run-status">
        <span className="live-dot" />
        <strong>{run.runId ?? "No Run"}</strong>
        <StatusPill status={run.status} />
        <span>{run.elapsed ?? "00:00:00"}</span>
      </div>

      <div className="new-run-group">
        <button className="command-button primary" type="button" onClick={onNewRun}>
          <Play size={16} fill="currentColor" />
          <span>New Run</span>
        </button>
      </div>

      <button className="profile-menu" aria-label="Local workspace session" type="button">
        <span className="avatar">PP</span>
        <ChevronDown size={15} />
      </button>
    </header>
  );
}
