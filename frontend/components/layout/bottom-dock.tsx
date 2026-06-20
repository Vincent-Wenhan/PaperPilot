"use client";

import { useState } from "react";
import type { AgentEvent } from "@/lib/mock-data";
import { LogsPanel } from "@/components/inspector/logs-panel";

type BottomDockTab = "logs" | "terminal" | "results" | "metrics";

type BottomDockProps = {
  events: AgentEvent[];
  commandResults?: string;
  resultSummary?: Record<string, unknown> | null;
  runId?: string;
};

export function BottomDock({ events, commandResults, resultSummary }: BottomDockProps) {
  const [activeTab, setActiveTab] = useState<BottomDockTab>("logs");
  const [collapsed, setCollapsed] = useState(false);

  return (
    <section className={`bottom-dock ${collapsed ? "collapsed" : ""}`}>
      <div className="bottom-dock-handle" onClick={() => setCollapsed(!collapsed)}>
        <span>Terminal / Output</span>
        <button className="icon-button" type="button" style={{ width: 24, height: 24, fontSize: 10 }}>
          {collapsed ? "▲" : "▼"}
        </button>
      </div>

      {!collapsed && (
        <>
          <div className="tab-list" role="tablist" aria-label="Bottom dock tabs" style={{ margin: "8px 12px 0" }}>
            {(["logs", "terminal", "results", "metrics"] as BottomDockTab[]).map((tab) => (
              <button
                key={tab}
                className={activeTab === tab ? "tab active" : "tab"}
                onClick={() => setActiveTab(tab)}
                type="button"
                style={{ textTransform: "capitalize" }}
              >
                {tab}
              </button>
            ))}
          </div>
          <div className="bottom-dock-content">
            {activeTab === "logs" && <LogsPanel events={events} />}
            {activeTab === "terminal" && (
              <pre className="terminal-block">
                <code>{commandResults || "No command output yet."}</code>
              </pre>
            )}
            {activeTab === "results" && (
              <pre className="terminal-block">
                <code>
                  {resultSummary
                    ? JSON.stringify(resultSummary, null, 2)
                    : "No run result available."}
                </code>
              </pre>
            )}
            {activeTab === "metrics" && (
              <div className="empty-state">Metrics coming soon.</div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
