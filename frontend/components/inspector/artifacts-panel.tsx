"use client";

import { StatusPill } from "@/components/status-pill";
import type { ArtifactItem } from "@/lib/mock-data";

type ArtifactsPanelProps = {
  artifactRows: ArtifactItem[];
};

export function ArtifactsPanel({ artifactRows }: ArtifactsPanelProps) {
  if (!artifactRows.length) {
    return <div className="empty-state">No artifacts for this run yet.</div>;
  }
  return (
    <div className="stack">
      {artifactRows.map((artifact) => (
        <div className="artifact-row" key={artifact.id}>
          <div>
            <strong>{artifact.name}</strong>
            <span>{artifact.kind}</span>
            <code>{artifact.path}</code>
          </div>
          <StatusPill status={artifact.status} />
        </div>
      ))}
    </div>
  );
}
