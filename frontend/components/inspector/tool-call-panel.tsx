"use client";

import { StatusPill } from "@/components/status-pill";
import type { ToolCall } from "@/lib/mock-data";

type ToolCallPanelProps = {
  toolCalls: ToolCall[];
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
