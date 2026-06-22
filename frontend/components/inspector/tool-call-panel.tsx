"use client";

import { StatusPill } from "@/components/status-pill";
import type { WorkbenchToolCallEvent } from "@/lib/workbench-types";

type ToolCallPanelProps = {
  toolCalls: WorkbenchToolCallEvent[];
};

export function ToolCallPanel({ toolCalls }: ToolCallPanelProps) {
  if (!toolCalls.length) {
    return <div className="empty-state">No tool calls have been emitted for this run.</div>;
  }

  return (
    <div className="stack">
      {toolCalls.map((call) => (
        <div className="tool-call" key={call.id}>
          <div>
            <div className="tool-call-meta">
              <code>{call.tool || call.eventType || "tool_event"}</code>
              {call.node && <span>{call.node}</span>}
              {call.agent && <span>{call.agent}</span>}
            </div>
            <p>{call.action || call.observation || "No message payload"}</p>
            {call.observation && call.action && <p>{call.observation}</p>}
            {call.payload && Object.keys(call.payload).length > 0 && (
              <pre className="payload-block">
                <code>{JSON.stringify(call.payload, null, 2)}</code>
              </pre>
            )}
          </div>
          <StatusPill status={call.status} />
        </div>
      ))}
    </div>
  );
}
