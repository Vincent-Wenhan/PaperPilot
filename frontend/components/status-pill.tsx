import type { WorkflowStatus } from "@/lib/mock-data";

const statusLabels: Record<WorkflowStatus, string> = {
  pending: "Pending",
  running: "Running",
  success: "Success",
  waiting_review: "Review",
  failed: "Failed",
  revised: "Revised",
};

export function StatusPill({ status }: { status: WorkflowStatus }) {
  return <span className={`status-pill status-${status}`}>{statusLabels[status]}</span>;
}
