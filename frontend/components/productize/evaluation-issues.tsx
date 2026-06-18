"use client";

import { AlertTriangle, CheckCircle, ShieldAlert, Info } from "lucide-react";
import type { WorkflowStatus } from "@/lib/mock-data";

export type EvaluationIssue = {
  id: string;
  message: string;
  severity: "low" | "medium" | "high" | "critical";
  target: string;
  suggestion: string;
  status: "open" | "accepted" | "revised";
};

const SEVERITY_ICONS: Record<string, typeof AlertTriangle> = {
  low: Info,
  medium: AlertTriangle,
  high: ShieldAlert,
  critical: ShieldAlert,
};

const SEVERITY_COLORS: Record<string, string> = {
  low: "var(--blue)",
  medium: "var(--amber)",
  high: "var(--red)",
  critical: "var(--red)",
};

type IssueCardProps = {
  issue: EvaluationIssue;
  onReduceScope?: (id: string) => void;
  onRevisePrd?: (id: string) => void;
  onRevisePrototype?: (id: string) => void;
  onAcceptWarning?: (id: string) => void;
};

export function IssueCard({
  issue,
  onReduceScope,
  onRevisePrd,
  onRevisePrototype,
  onAcceptWarning,
}: IssueCardProps) {
  const Icon = SEVERITY_ICONS[issue.severity] ?? Info;
  const color = SEVERITY_COLORS[issue.severity] ?? "var(--text-muted)";

  return (
    <div className={`issue-card severity-${issue.severity}`}>
      <div className="issue-card-header">
        <Icon size={16} style={{ color }} />
        <div>
          <strong>{issue.message}</strong>
          <span className="eyebrow">
            Severity: {issue.severity} · Target: {issue.target}
          </span>
        </div>
        <span className={`issue-status status-${issue.status}`}>{issue.status}</span>
      </div>
      <p className="issue-suggestion">{issue.suggestion}</p>
      {issue.status === "open" && (
        <div className="action-row" style={{ marginTop: 8 }}>
          {onReduceScope && (
            <button
              className="command-button"
              type="button"
              onClick={() => onReduceScope(issue.id)}
            >
              Reduce MVP Scope
            </button>
          )}
          {onRevisePrd && (
            <button
              className="command-button"
              type="button"
              onClick={() => onRevisePrd(issue.id)}
            >
              Revise PRD
            </button>
          )}
          {onRevisePrototype && (
            <button
              className="command-button"
              type="button"
              onClick={() => onRevisePrototype(issue.id)}
            >
              Revise Prototype
            </button>
          )}
          {onAcceptWarning && (
            <button
              className="command-button"
              type="button"
              onClick={() => onAcceptWarning(issue.id)}
            >
              Accept with Warning
            </button>
          )}
        </div>
      )}
    </div>
  );
}

type ProductizeTabsProps = {
  activeTab: string;
  onTabChange: (tab: string) => void;
};

const PRODUCTIZE_TABS = [
  { id: "research", label: "Research" },
  { id: "product", label: "Product" },
  { id: "prototype", label: "Prototype" },
  { id: "evaluation", label: "Evaluation" },
];

export function ProductizeTabs({ activeTab, onTabChange }: ProductizeTabsProps) {
  return (
    <div className="tab-list" role="tablist" aria-label="Productize tabs">
      {PRODUCTIZE_TABS.map((tab) => (
        <button
          key={tab.id}
          className={activeTab === tab.id ? "tab active" : "tab"}
          onClick={() => onTabChange(tab.id)}
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

const MOCK_ISSUES: EvaluationIssue[] = [
  {
    id: "issue-1",
    message: "MVP scope is too broad for a first prototype",
    severity: "medium",
    target: "Product Planner",
    suggestion:
      "Reduce features to upload → mock output → explanation → download report.",
    status: "open",
  },
  {
    id: "issue-2",
    message: "Missing safety warning for generated content",
    severity: "high",
    target: "Prototype Builder",
    suggestion:
      "Add a safety disclaimer banner and content filter boundary in the adapter.",
    status: "open",
  },
  {
    id: "issue-3",
    message: "Demo readiness score is below threshold",
    severity: "low",
    target: "Product Evaluator",
    suggestion:
      "Consider simplifying the flow to a single-page mock with clear results.",
    status: "accepted",
  },
];

export function getMockIssues(): EvaluationIssue[] {
  return MOCK_ISSUES.map((i) => ({ ...i }));
}
