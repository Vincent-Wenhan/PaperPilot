"use client";

import { AlertTriangle, CheckCircle, ShieldAlert, Info } from "lucide-react";

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

export function issuesFromRunResult(result: Record<string, unknown>): EvaluationIssue[] {
  const issues: EvaluationIssue[] = [];
  let counter = 0;

  const problems = Array.isArray(result["detected_problems"])
    ? (result["detected_problems"] as string[])
    : [];
  const suggestions = Array.isArray(result["revision_suggestions"])
    ? (result["revision_suggestions"] as string[])
    : [];
  const warnings = Array.isArray(result["safety_warnings"])
    ? (result["safety_warnings"] as string[])
    : [];

  for (const problem of problems) {
    issues.push({
      id: `eval-problem-${counter++}`,
      message: problem,
      severity: "high",
      target: "Product Evaluator",
      suggestion: "",
      status: "open",
    });
  }
  for (const suggestion of suggestions) {
    issues.push({
      id: `eval-suggestion-${counter++}`,
      message: suggestion,
      severity: "medium",
      target: "Product Planner",
      suggestion: "",
      status: "open",
    });
  }
  for (const warning of warnings) {
    issues.push({
      id: `eval-warning-${counter++}`,
      message: warning,
      severity: "critical",
      target: "Safety Reviewer",
      suggestion: "",
      status: "open",
    });
  }

  return issues;
}