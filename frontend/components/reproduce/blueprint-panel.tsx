"use client";

import { CheckCircle, AlertTriangle, XCircle, Info } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/workbench-types";

export type EvidenceItem = {
  path: string;
  label: string;
  tool: string;
  found: boolean;
  warning?: string;
};

export type BlueprintCoverage = {
  entrypoints: number;
  covered: number;
  status: WorkflowStatus;
};

type ReproduceBlueprintProps = {
  files: Array<{ path: string; status: WorkflowStatus }>;
  coverage: BlueprintCoverage;
  syntaxStatus: WorkflowStatus;
  smokeTestStatus: WorkflowStatus;
  sandboxVerify: WorkflowStatus;
  codeReviewVerdict: string;
  revisionSuggestions: string[];
  secondReviewResult: string;
  finalDiagnosis: string;
};

export function ReproduceBlueprintPanel({
  files,
  coverage,
  syntaxStatus,
  smokeTestStatus,
  sandboxVerify,
  codeReviewVerdict,
  revisionSuggestions,
  secondReviewResult,
  finalDiagnosis,
}: ReproduceBlueprintProps) {
  return (
    <div className="stack">
      <div className="blueprint-section">
        <p className="eyebrow">Implementation Blueprint</p>
        <div className="blueprint-grid">
          <span>Entrypoints found</span>
          <strong>{coverage.entrypoints}</strong>
          <span>Blueprint covered</span>
          <strong>{coverage.covered} / {coverage.entrypoints}</strong>
          <span>Coverage status</span>
          <StatusPill status={coverage.status} />
        </div>
      </div>

      <div className="blueprint-section">
        <p className="eyebrow">Generated Files</p>
        <ul className="file-status-list">
          {files.map((f) => (
            <li key={f.path}>
              <span>{f.path}</span>
              <StatusPill status={f.status} />
            </li>
          ))}
        </ul>
      </div>

      <div className="blueprint-section">
        <p className="eyebrow">Quality Checks</p>
        <div className="check-row">
          <span>Syntax check</span>
          <StatusPill status={syntaxStatus} />
        </div>
        <div className="check-row">
          <span>Smoke test</span>
          <StatusPill status={smokeTestStatus} />
        </div>
        <div className="check-row">
          <span>Sandbox verify</span>
          <StatusPill status={sandboxVerify} />
        </div>
      </div>

      <div className="blueprint-section">
        <p className="eyebrow">Code Review</p>
        <p className="review-verdict">{codeReviewVerdict}</p>
        {revisionSuggestions.length > 0 && (
          <ul className="suggestion-list">
            {revisionSuggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        )}
        {secondReviewResult && (
          <div className="second-review">
            <span className="eyebrow">Second Review</span>
            <p>{secondReviewResult}</p>
          </div>
        )}
      </div>

      <div className="blueprint-section">
        <p className="eyebrow">Final Diagnosis</p>
        <p>{finalDiagnosis}</p>
      </div>
    </div>
  );
}

type EvidenceTraceProps = {
  evidence: EvidenceItem[];
};

const ICON_MAP: Record<string, typeof CheckCircle> = {
  found: CheckCircle,
  warning: AlertTriangle,
  missing: XCircle,
};

const COLOR_MAP: Record<string, string> = {
  found: "var(--green)",
  warning: "var(--amber)",
  missing: "var(--red)",
};

export function EvidenceTrace({ evidence }: EvidenceTraceProps) {
  return (
    <div className="evidence-trace">
      <p className="eyebrow">Repository Evidence Trace</p>
      <ul>
        {evidence.map((item) => {
          const kind = item.warning ? "warning" : item.found ? "found" : "missing";
          const Icon = ICON_MAP[kind];
          return (
            <li key={item.path} className={`evidence-item ${kind}`}>
              <Icon size={14} style={{ color: COLOR_MAP[kind] }} />
              <div>
                <strong>{item.label}</strong>
                <code>{item.tool}</code>
                {item.warning && <p className="evidence-warning">{item.warning}</p>}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function getMockReproduceBlueprint(): ReproduceBlueprintProps {
  return {
    files: [
      { path: "workspace/generated_code/main.py", status: "success" },
      { path: "workspace/generated_code/config.py", status: "success" },
      { path: "outputs/vit/reproduction_plan.md", status: "success" },
      { path: "outputs/vit/run.sh", status: "waiting_review" },
      { path: "outputs/vit/report.md", status: "pending" },
    ],
    coverage: { entrypoints: 4, covered: 3, status: "running" },
    syntaxStatus: "success",
    smokeTestStatus: "waiting_review",
    sandboxVerify: "pending",
    codeReviewVerdict:
      "Generated entrypoint is structurally correct. Missing dataset path validation.",
    revisionSuggestions: [
      "Add dataset path existence check before training.",
      "Move hardcoded constants to config.py.",
    ],
    secondReviewResult:
      "Both revision suggestions were applied. Code quality now acceptable for demo.",
    finalDiagnosis:
      "Reproduce pipeline completed with minor warnings. Generated code is safe to review and run under sandbox mode.",
  };
}

export function getMockEvidence(): EvidenceItem[] {
  return [
    {
      path: "train.py",
      label: "Found training entrypoint",
      tool: "code_search('argparse')",
      found: true,
    },
    {
      path: "eval.py",
      label: "Found evaluation script",
      tool: "code_search('eval')",
      found: true,
    },
    {
      path: "requirements.txt",
      label: "Parsed requirements",
      tool: "parse_requirements()",
      found: true,
    },
    {
      path: "train.py:argparse",
      label: "Found argparse arguments",
      tool: "python_ast_summary('train.py')",
      found: true,
    },
    {
      path: "checkpoints/",
      label: "Checkpoint path unclear",
      tool: "find_dataset_paths()",
      found: false,
      warning: "No checkpoint directory found in repo root.",
    },
    {
      path: "data/",
      label: "Dataset preprocessing missing",
      tool: "find_dataset_paths()",
      found: false,
      warning: "No dataset preprocessing script detected.",
    },
  ];
}
