import type { ReactNode } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  CircleDotDashed,
  Clock3,
  FileText,
  Loader2,
  XCircle,
} from "lucide-react";

export type PartStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "rejected"
  | "waiting_approval";

export type MessagePart =
  | { type: "text"; id: string; text: string }
  | { type: "reasoning-summary"; id: string; text: string }
  | { type: "tool"; id: string; toolCallId: string }
  | { type: "artifact"; id: string; artifactId: string; name?: string }
  | { type: "plan-review"; id: string; interruptId: string }
  | { type: "status"; id: string; label: string; status: PartStatus }
  | { type: "error"; id: string; title: string; detail: string };

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  agentId?: string;
  parts: MessagePart[];
  status: "streaming" | "completed" | "failed";
  createdAt?: string;
};

export const STATUS_ICONS: Record<PartStatus, typeof CheckCircle2> = {
  pending: Clock3,
  running: Loader2,
  succeeded: CheckCircle2,
  failed: XCircle,
  rejected: XCircle,
  waiting_approval: CircleDotDashed,
};

export const STATUS_TONES: Record<PartStatus, "ok" | "warn" | "danger" | "neutral"> = {
  pending: "neutral",
  running: "warn",
  succeeded: "ok",
  failed: "danger",
  rejected: "danger",
  waiting_approval: "warn",
};

export function PartShell({
  icon,
  label,
  tone = "neutral",
  children,
}: {
  icon: typeof CheckCircle2;
  label: string;
  tone?: "ok" | "warn" | "danger" | "neutral";
  children: ReactNode;
}) {
  return (
    <div className={`message-part tone-${tone}`} data-part-label={label}>
      <div className="message-part-header">
        <icon size={14} />
        <span className="message-part-label">{label}</span>
      </div>
      <div className="message-part-body">{children}</div>
    </div>
  );
}

export function TextPart({ text }: { text: string }) {
  return <p className="message-text whitespace-pre-wrap">{text}</p>;
}

export function ReasoningSummaryPart({ text }: { text: string }) {
  return (
    <details className="message-part reasoning-summary">
      <summary className="message-part-header cursor-pointer">
        <AlertTriangle size={14} />
        <span>Reasoning summary</span>
      </summary>
      <div className="message-part-body">
        <p className="whitespace-pre-wrap text-sm">{text}</p>
      </div>
    </details>
  );
}

export function ErrorPart({ title, detail }: { title: string; detail: string }) {
  return (
    <PartShell icon={AlertTriangle} label={title} tone="danger">
      <p className="text-sm">{detail}</p>
    </PartShell>
  );
}

export function ArtifactPart({
  artifactId,
  name,
}: {
  artifactId: string;
  name?: string;
}) {
  return (
    <PartShell icon={FileText} label="Artifact" tone="ok">
      <div className="text-sm">
        <div className="font-medium">{name ?? artifactId}</div>
        <div className="text-xs text-muted-foreground">{artifactId}</div>
      </div>
    </PartShell>
  );
}

export function StatusPart({ label, status }: { label: string; status: PartStatus }) {
  const Icon = STATUS_ICONS[status];
  const tone = STATUS_TONES[status];
  return (
    <PartShell icon={Icon} label={label} tone={tone}>
      <span className="text-xs uppercase tracking-wide">{status.replace(/_/g, " ")}</span>
    </PartShell>
  );
}
