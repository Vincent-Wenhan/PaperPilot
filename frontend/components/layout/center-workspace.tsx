"use client";

import type { AgentEvent, PlanStep, RunMode, WorkflowStatus } from "@/lib/mock-data";
import type { EvaluationIssue } from "@/components/productize/evaluation-issues";
import { IssueCard } from "@/components/productize/evaluation-issues";
import { WorkflowGraph, type GraphNodeData } from "@/components/workflow-graph";
import { WorkbenchTabs, type WorkbenchTabId } from "@/components/workbench/workbench-tabs";
import { ActivityPanel } from "@/components/workbench/activity-panel";

type CenterWorkspaceProps = {
  mode: RunMode;
  notice: string;
  planState: PlanStep[];
  timelineEvents: AgentEvent[];
  runStatus: WorkflowStatus;
  hasRun: boolean;
  graphNodes?: GraphNodeData[];
  activeTab: WorkbenchTabId;
  onTabChange: (tab: WorkbenchTabId) => void;
  onTogglePlanStep: (stepId: string) => void;
  onApprovePlan: () => void;
  onContinueRun: () => void;
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
  onTabChange,
  onTogglePlanStep,
  onApprovePlan,
  onContinueRun,
  evaluationIssues,
}: CenterWorkspaceProps) {
  void planState;
  void onTogglePlanStep;
  void onApprovePlan;

  return (
    <section className="center-workspace" data-run-status={runStatus}>
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
              <h2>PRD / MVP / Prototype</h2>
            </div>
          </div>
          <div className="empty-state">
            Product design content will appear after running a productize pipeline. Check the
            Artifacts and Code tabs in the Inspector for generated outputs.
          </div>
        </section>
      )}
    </section>
  );
}
