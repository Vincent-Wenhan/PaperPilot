"use client";

import { StatusPill } from "@/components/status-pill";
import type { WorkbenchToolCallEvent } from "@/lib/workbench-types";

type ToolCallPanelProps = {
  toolCalls: WorkbenchToolCallEvent[];
};

export function ToolCallPanel({ toolCalls }: ToolCallPanelProps) {
  return (
    <div className="stack">
      {toolCalls.map((call) => (
        <div className="tool-call" key={call.id}>
          <div>
            <code>{call.action}</code>
            <p>{call.observation}</p>
          </div>
          <StatusPill status={call.status} />
        </div>
      ))}
    </div>
  );
}
