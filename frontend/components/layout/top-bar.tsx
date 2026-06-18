"use client";

import { Layers } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/mock-data";

type TopBarProps = {
  project: string;
  mode: string;
  model: string;
  summary: string;
  runStatus: WorkflowStatus;
};

export function TopBar({ project, mode, model, summary, runStatus }: TopBarProps) {
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

      <div className="topbar-context">
        <span>Project: {project}</span>
        <span>Mode: {mode}</span>
        <span>Model: {model}</span>
      </div>

      <div className="run-state">
        <span>{summary || "No backend run created yet"}</span>
        <StatusPill status={runStatus} />
      </div>
    </header>
  );
}
