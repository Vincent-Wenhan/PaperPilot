"use client";

import { CheckCircle2, Circle } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import type { AgentEvent } from "@/lib/mock-data";

type ActivityPanelProps = {
  events: AgentEvent[];
};

export function ActivityPanel({ events }: ActivityPanelProps) {
  return (
    <section className="activity-panel" aria-label="Activity">
      <div className="panel-heading">
        <h2>Activity</h2>
      </div>
      <div className="timeline">
        {events.length === 0 && (
          <div className="empty-state">No events yet. Create a run to see agent progress.</div>
        )}
        {events.map((event) => (
          <article className="timeline-event" key={event.id}>
            {event.status === "success" ? <CheckCircle2 size={15} /> : <Circle size={15} />}
            <time>{event.time}</time>
            <p><strong>{event.agent}</strong> {event.message}</p>
            <StatusPill status={event.status} />
          </article>
        ))}
      </div>
    </section>
  );
}
