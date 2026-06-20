"use client";

import { Clock3 } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import type { AgentEvent } from "@/lib/mock-data";

type ActivityPanelProps = {
  events: AgentEvent[];
};

export function ActivityPanel({ events }: ActivityPanelProps) {
  return (
    <div className="tool-panel timeline-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Event stream</p>
          <h2>Agent trace</h2>
        </div>
        <Clock3 size={17} />
      </div>
      <div className="timeline">
        {events.length === 0 && (
          <div className="empty-state">No events yet. Create a run to see agent progress.</div>
        )}
        {events.map((event) => (
          <article className="timeline-event" key={event.id}>
            <div className={`event-dot status-${event.status}`} />
            <div>
              <span>{event.time}</span>
              <strong>{event.agent}</strong>
              <p>{event.message}</p>
            </div>
            <StatusPill status={event.status} />
          </article>
        ))}
      </div>
    </div>
  );
}
