"use client";

import type { AgentEvent, PlanStep, RunMode, WorkflowStatus } from "@/lib/workbench-types";
import type { EvaluationIssue } from "@/components/productize/evaluation-issues";
import { IssueCard } from "@/components/productize/evaluation-issues";
import type { ApiProductProposal, ApiRevisionAction, ApiRunResult } from "@/lib/api";
import { WorkflowGraph, type GraphNodeData } from "@/components/workflow-graph";
import { WorkbenchTabs, type WorkbenchTabId } from "@/components/workbench/workbench-tabs";
import { ActivityPanel } from "@/components/workbench/activity-panel";
import { StatusPill } from "@/components/status-pill";

export type WorkspaceSectionContext = {
  projectId: string;
  task: string;
  paperInput: string;
  repoInput: string;
  mode: RunMode;
  model: string;
  baseUrl: string;
  goal: string;
  hardware: string;
  gpuInfo: string;
  mockMode: boolean;
  runId?: string;
  runStatus: WorkflowStatus;
  pendingActions: number;
  eventCount: number;
  generatedFiles: number;
  pipelineStatus?: string;
  productGoal: string;
  targetUser: string;
};

type CenterWorkspaceProps = {
  mode: RunMode;
  notice: string;
  planState: PlanStep[];
  timelineEvents: AgentEvent[];
  runStatus: WorkflowStatus;
  hasRun: boolean;
  graphNodes?: GraphNodeData[];
  activeTab: WorkbenchTabId;
  activeNavId: string;
  sectionContext: WorkspaceSectionContext;
  onTabChange: (tab: WorkbenchTabId) => void;
  onTogglePlanStep: (stepId: string) => void;
  onApprovePlan: () => void;
  onContinueRun: () => void;
  onOpenRunDrawer: () => void;
  onShowWorkflow: () => void;
  onRequestRevision?: (issueId: string, action: ApiRevisionAction) => void;
  onExecuteProductizeProposal?: (proposalIndex: number) => void;
  executingProductizeProposalIndex?: number | null;
  runResult?: ApiRunResult | null;
  evaluationIssues?: EvaluationIssue[];
};

export function CenterWorkspace({
  mode,
  notice,
  planState,
  timelineEvents,
  runStatus,
  hasRun,
  graphNodes,
  activeTab,
  activeNavId,
  sectionContext,
  onTabChange,
  onTogglePlanStep,
  onApprovePlan,
  onContinueRun,
  onOpenRunDrawer,
  onShowWorkflow,
  onRequestRevision,
  onExecuteProductizeProposal,
  executingProductizeProposalIndex,
  runResult,
  evaluationIssues,
}: CenterWorkspaceProps) {
  void planState;
  void onTogglePlanStep;
  void onApprovePlan;
  const showSectionPanel = activeNavId !== "run";

  return (
    <section className="center-workspace" data-run-status={runStatus}>
      {showSectionPanel ? (
        <WorkspaceSectionPanel
          activeNavId={activeNavId}
          context={sectionContext}
          onOpenRunDrawer={onOpenRunDrawer}
          onShowWorkflow={onShowWorkflow}
        />
      ) : (
        <>
          <WorkbenchTabs activeTab={activeTab} onTabChange={onTabChange} />

          {activeTab === "workflow" && (
            <div className="workflow-surface">
              <section className="graph-panel" aria-label="Workflow graph panel">
                <div className="graph-context" title={notice}>
                  <span>{mode === "reproduce" ? "Reproduce workflow" : "Product Design workflow"}</span>
                  <button className="refresh-link" type="button" onClick={onContinueRun}>Refresh</button>
                </div>
                {hasRun ? (
                  <WorkflowGraph nodes={graphNodes} />
                ) : (
                  <div className="empty-state">
                    No backend run yet. Upload a PDF and create a run to see pipeline progress.
                  </div>
                )}
              </section>
              <ActivityPanel events={timelineEvents} />
            </div>
          )}

          {activeTab === "evaluation" && (
            <section className="tool-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Quality</p>
                  <h2>Evaluation issues</h2>
                </div>
              </div>
              {evaluationIssues && evaluationIssues.length > 0 ? (
                <div className="stack">
                  {evaluationIssues.map((issue) => (
                    <IssueCard
                      key={issue.id}
                      issue={issue}
                      onReduceScope={
                        onRequestRevision
                          ? (id) => onRequestRevision(id, "reduce_mvp_scope")
                          : undefined
                      }
                      onRevisePrd={
                        onRequestRevision
                          ? (id) => onRequestRevision(id, "revise_prd")
                          : undefined
                      }
                      onRevisePrototype={
                        onRequestRevision
                          ? (id) => onRequestRevision(id, "revise_prototype")
                          : undefined
                      }
                      onAcceptWarning={
                        onRequestRevision
                          ? (id) => onRequestRevision(id, "accept_with_warning")
                          : undefined
                      }
                    />
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  No evaluation issues. Run a productize pipeline to see evaluator feedback.
                </div>
              )}
            </section>
          )}

          {activeTab === "product" && (
            <section className="tool-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Product Design</p>
                  <h2>
                    {runResult?.productize_stage === "proposal_review"
                      ? "Choose a Product Proposal"
                      : "PRD / MVP / Prototype"}
                  </h2>
                </div>
              </div>
              {runResult?.productize_proposals?.length ? (
                <ProductProposalList
                  proposals={runResult.productize_proposals}
                  selectedProposal={runResult.selected_proposal}
                  executingIndex={executingProductizeProposalIndex ?? null}
                  onExecute={onExecuteProductizeProposal}
                />
              ) : (
                <div className="empty-state">
                  Product design content will appear after running a productize pipeline. Check the
                  Artifacts and Code tabs in the Inspector for generated outputs.
                </div>
              )}
            </section>
          )}
        </>
      )}
    </section>
  );
}

function ProductProposalList({
  proposals,
  selectedProposal,
  executingIndex,
  onExecute,
}: {
  proposals: ApiProductProposal[];
  selectedProposal?: ApiProductProposal;
  executingIndex?: number | null;
  onExecute?: (proposalIndex: number) => void;
}) {
  return (
    <div className="stack">
      <div className="empty-state product-proposal-guidance" role="status">
        Review the proposal options below, compare target users, core features, and risks, then select one proposal to scaffold the MVP.
      </div>
      {proposals.map((proposal, index) => {
        const features = proposal.prd?.core_features ?? [];
        const risks = proposal.risks ?? proposal.prd?.risks ?? [];
        const selected = sameProposal(proposal, selectedProposal);
        const executing = executingIndex === index;
        return (
          <article
            className={`issue-card${selected ? " proposal-selected" : ""}`}
            key={`${proposal.product_name ?? "proposal"}-${index}`}
            aria-label={`Product proposal ${index + 1}: ${proposal.product_name || proposal.prd?.product_name || "Untitled product"}`}
          >
            <div className="issue-card-header">
              <div>
                <p className="eyebrow">Proposal {index + 1}</p>
                <h3>{proposal.product_name || proposal.prd?.product_name || "Untitled product"}</h3>
              </div>
              <StatusPill status={selected ? "success" : "waiting_review"} />
            </div>
            {selected ? (
              <div className="empty-state product-proposal-selected" role="status">
                Selected proposal
              </div>
            ) : null}
            <div className="detail-grid">
              <div className="detail-row">
                <span>Target user</span>
                <strong>{proposal.target_user || "Not set"}</strong>
              </div>
              <div className="detail-row">
                <span>Goal</span>
                <strong>{proposal.product_goal || "Not set"}</strong>
              </div>
              <div className="detail-row">
                <span>JTBD</span>
                <strong>{proposal.jtbd || "Not set"}</strong>
              </div>
            </div>
            {features.length ? (
              <div className="issue-list">
                <strong>Core features</strong>
                <ul>
                  {features.slice(0, 5).map((feature) => (
                    <li key={feature}>{feature}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {risks.length ? (
              <div className="issue-list">
                <strong>Risks</strong>
                <ul>
                  {risks.slice(0, 3).map((risk) => (
                    <li key={risk}>{risk}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="section-actions">
              <button
                type="button"
                className="secondary-action"
                onClick={() => onExecute?.(index)}
                disabled={!onExecute || executing}
              >
                {executing ? "Selecting Proposal..." : "Select & Scaffold Proposal"}
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function sameProposal(left: ApiProductProposal, right?: ApiProductProposal) {
  if (!right) {
    return false;
  }
  const leftName = left.product_name || left.prd?.product_name || "";
  const rightName = right.product_name || right.prd?.product_name || "";
  return Boolean(leftName && rightName && leftName === rightName);
}

function WorkspaceSectionPanel({
  activeNavId,
  context,
  onOpenRunDrawer,
  onShowWorkflow,
}: {
  activeNavId: string;
  context: WorkspaceSectionContext;
  onOpenRunDrawer: () => void;
  onShowWorkflow: () => void;
}) {
  const section = sectionCopy(activeNavId);
  const rows = sectionRows(activeNavId, context);

  return (
    <section className="tool-panel workspace-section-panel" aria-label={section.title}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{section.eyebrow}</p>
          <h2>{section.title}</h2>
        </div>
        {activeNavId === "project" || activeNavId === "agents" ? (
          <StatusPill status={context.runStatus} />
        ) : null}
      </div>

      <div className="detail-grid">
        {rows.map((row) => (
          <div className="detail-row" key={row.label}>
            <span>{row.label}</span>
            <strong>{row.value || "Not set"}</strong>
          </div>
        ))}
      </div>

      <div className="section-actions">
        {activeNavId === "run" ? null : (
          <button type="button" className="secondary-action" onClick={onOpenRunDrawer}>
            Edit Run Inputs
          </button>
        )}
        <button type="button" className="secondary-action" onClick={onShowWorkflow}>
          Open Workflow
        </button>
      </div>
    </section>
  );
}

function sectionCopy(activeNavId: string): { eyebrow: string; title: string } {
  if (activeNavId === "paper") return { eyebrow: "Paper", title: "Paper Input" };
  if (activeNavId === "repo") return { eyebrow: "Repository", title: "Repository Input" };
  if (activeNavId === "agents") return { eyebrow: "Agents", title: "Agent Runtime" };
  if (activeNavId === "settings") return { eyebrow: "Settings", title: "Runtime Settings" };
  return { eyebrow: "Project", title: "Project Overview" };
}

function sectionRows(
  activeNavId: string,
  context: WorkspaceSectionContext,
): Array<{ label: string; value: string }> {
  if (activeNavId === "paper") {
    return [
      { label: "PDF", value: context.paperInput },
      { label: "Task", value: context.task },
      { label: "Goal", value: context.goal },
    ];
  }
  if (activeNavId === "repo") {
    return [
      { label: "Repository", value: context.repoInput },
      { label: "Hardware", value: [context.hardware, context.gpuInfo].filter(Boolean).join(" / ") },
      { label: "Generated files", value: String(context.generatedFiles) },
    ];
  }
  if (activeNavId === "agents") {
    return [
      { label: "Pipeline", value: context.pipelineStatus || context.runStatus },
      { label: "Events", value: String(context.eventCount) },
      { label: "Pending actions", value: String(context.pendingActions) },
      { label: "Model", value: context.model },
    ];
  }
  if (activeNavId === "settings") {
    return [
      { label: "Mode", value: context.mode },
      { label: "Base URL", value: context.baseUrl },
      { label: "Model", value: context.model },
      { label: "Mock mode", value: context.mockMode ? "Enabled" : "Disabled" },
    ];
  }
  return [
    { label: "Project", value: context.projectId },
    { label: "Run", value: context.runId || "No active run" },
    { label: "Status", value: context.runStatus },
    { label: "Product goal", value: context.productGoal || context.targetUser },
  ];
}
