import {
  AlertTriangle,
  CheckCircle2,
  CircleDotDashed,
  Clock3,
  FileText,
  type LucideIcon,
} from "lucide-react";

import type { ConversationMessage, MessagePart } from "./types";

export function MessageView({ message }: { message: ConversationMessage }) {
  return (
    <article className="chat-message" data-role={message.role}>
      <header className="chat-message-header">
        <span className="chat-message-agent">
          {message.role === "user" ? "You" : (message.agentId ?? "PaperPilot")}
        </span>
        {message.status === "streaming" ? (
          <span className="chat-message-streaming">working…</span>
        ) : null}
      </header>
      <div className="chat-message-body">
        {message.parts.map((part) => (
          <PartRenderer key={part.id} part={part} />
        ))}
      </div>
    </article>
  );
}

export function PartRenderer({ part }: { part: MessagePart }) {
  switch (part.type) {
    case "text":
      return <p className="message-text whitespace-pre-wrap">{part.text}</p>;
    case "reasoning-summary":
      return (
        <details className="message-part reasoning-summary">
          <summary>Reasoning summary</summary>
          <p className="whitespace-pre-wrap text-sm">{part.text}</p>
        </details>
      );
    case "tool":
      return (
        <PartShell icon={CircleDotDashed} label="Tool call" tone="neutral">
          <span className="text-sm font-mono">{part.toolCallId}</span>
        </PartShell>
      );
    case "artifact":
      return (
        <PartShell icon={FileText} label="Artifact" tone="ok">
          <div className="text-sm">
            <div className="font-medium">{part.name ?? part.artifactId}</div>
            <div className="text-xs text-muted-foreground">{part.artifactId}</div>
          </div>
        </PartShell>
      );
    case "plan-review":
      return (
        <PartShell icon={Clock3} label="Plan review" tone="warn">
          <span className="text-xs">interrupt {part.interruptId}</span>
        </PartShell>
      );
    case "status":
      return <StatusInline label={part.label} status={part.status} />;
    case "error":
      return (
        <PartShell icon={AlertTriangle} label={part.title} tone="danger">
          <p className="text-sm">{part.detail}</p>
        </PartShell>
      );
  }
}

function StatusInline({
  label,
  status,
}: {
  label: string;
  status: "pending" | "running" | "succeeded" | "failed" | "rejected" | "waiting_approval";
}) {
  const ICONS: Record<typeof status, LucideIcon> = {
    pending: Clock3,
    running: CircleDotDashed,
    succeeded: CheckCircle2,
    failed: AlertTriangle,
    rejected: AlertTriangle,
    waiting_approval: Clock3,
  };
  const Icon = ICONS[status];
  return (
    <div className="message-part status-inline" data-status={status}>
      <Icon size={14} />
      <span className="message-part-label">{label}</span>
      <span className="message-part-status">{status.replace(/_/g, " ")}</span>
    </div>
  );
}

export function PartShell({
  icon: Icon,
  label,
  tone = "neutral",
  children,
}: {
  icon: LucideIcon;
  label: string;
  tone?: "ok" | "warn" | "danger" | "neutral";
  children: React.ReactNode;
}) {
  return (
    <div className={`message-part tone-${tone}`} data-part-label={label}>
      <div className="message-part-header">
        <Icon size={14} />
        <span className="message-part-label">{label}</span>
      </div>
      <div className="message-part-body">{children}</div>
    </div>
  );
}
