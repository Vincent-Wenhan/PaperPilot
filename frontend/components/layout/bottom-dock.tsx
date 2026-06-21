"use client";

import { Radio, Trash2 } from "lucide-react";
import { useState } from "react";

import { LogsPanel } from "@/components/inspector/logs-panel";
import type { AgentEvent } from "@/lib/workbench-types";

type BottomDockTab = "logs" | "terminal" | "results";

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
];

export function BottomDock({ events, commandResults, resultSummary }: BottomDockProps) {
  const [activeTab, setActiveTab] = useState<BottomDockTab>("logs");
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
          <span className="console-control live" aria-label="Live">
            <Radio size={14} /> Live
          </span>
          <button className="console-control" type="button" aria-label="Clear" onClick={() => setCleared(true)}>
            <Trash2 size={14} /> Clear
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
          </>
        )}
      </div>
    </section>
  );
}
