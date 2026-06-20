"use client";

import { MoreVertical, Pause, Radio, Trash2 } from "lucide-react";
import { useState } from "react";

import { LogsPanel } from "@/components/inspector/logs-panel";
import type { AgentEvent } from "@/lib/mock-data";

type BottomDockTab = "logs" | "terminal" | "results" | "metrics";

type BottomDockProps = {
  events: AgentEvent[];
  commandResults?: string;
  resultSummary?: Record<string, unknown> | null;
  runId?: string;
};

const TABS: Array<{ id: BottomDockTab; label: string }> = [
  { id: "logs", label: "Logs" },
  { id: "terminal", label: "Terminal" },
  { id: "results", label: "Results" },
  { id: "metrics", label: "Metrics" },
];

export function BottomDock({ events, commandResults, resultSummary }: BottomDockProps) {
  const [activeTab, setActiveTab] = useState<BottomDockTab>("logs");
  const [paused, setPaused] = useState(false);
  const [cleared, setCleared] = useState(false);

  return (
    <section className="bottom-dock" aria-label="Run console">
      <header className="console-toolbar">
        <div className="console-tabs" role="tablist" aria-label="Bottom dock tabs">
          {TABS.map((tab) => (
            <button
              aria-selected={activeTab === tab.id}
              className={activeTab === tab.id ? "console-tab active" : "console-tab"}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="console-actions">
          <button className="console-control live" type="button" aria-label="Live">
            <Radio size={14} /> Live
          </button>
          <button className="console-control" type="button" aria-label="Pause" onClick={() => setPaused(!paused)}>
            <Pause size={14} /> {paused ? "Resume" : "Pause"}
          </button>
          <button className="console-control" type="button" aria-label="Clear" onClick={() => setCleared(true)}>
            <Trash2 size={14} /> Clear
          </button>
          <button className="icon-button console-more" aria-label="More console actions" type="button">
            <MoreVertical size={16} />
          </button>
        </div>
      </header>

      <div className="bottom-dock-content" role="tabpanel">
        {cleared ? <div className="empty-state">Console cleared.</div> : (
          <>
            {activeTab === "logs" && <LogsPanel events={events} />}
            {activeTab === "terminal" && (
              <pre className="terminal-block"><code>{commandResults || "No command output yet."}</code></pre>
            )}
            {activeTab === "results" && (
              <pre className="terminal-block"><code>{resultSummary ? JSON.stringify(resultSummary, null, 2) : "No run result available."}</code></pre>
            )}
            {activeTab === "metrics" && <div className="empty-state">Metrics will appear after a completed run.</div>}
          </>
        )}
      </div>
    </section>
  );
}
