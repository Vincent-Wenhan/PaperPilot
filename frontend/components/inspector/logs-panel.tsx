"use client";

import type { AgentEvent } from "@/lib/mock-data";

type LogsPanelProps = {
  events: AgentEvent[];
};

export function LogsPanel({ events }: LogsPanelProps) {
  return (
    <pre className="terminal-block">
      <code>
        {events.length
          ? events
              .map(
                (event) =>
                  `> ${event.eventType} ${event.agent}: ${event.message}`,
              )
              .join("\n")
          : "> no backend events for this run yet"}
      </code>
    </pre>
  );
}
