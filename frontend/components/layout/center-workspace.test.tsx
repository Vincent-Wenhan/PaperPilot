import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CenterWorkspace } from "@/components/layout/center-workspace";
import type { GraphNodeData } from "@/components/workflow-graph";

vi.mock("@/components/workflow-graph", () => ({
  WorkflowGraph: () => <div aria-label="Workflow graph" />,
}));

describe("center workspace workflow observability", () => {
  it("shows verification summary metrics above the workflow graph", () => {
    render(
      <CenterWorkspace
        mode="reproduce"
        notice=""
        planState={[]}
        timelineEvents={[]}
        runStatus="running"
        hasRun
        graphNodes={[
          graphNode("parse", "success", {
            outputArtifacts: ["paper_understanding"],
          }),
          graphNode("implementation", "running", {
            inputArtifacts: ["implementation_contract"],
            outputArtifacts: ["generated_project"],
            toolCalls: [{ eventId: "tool_1", type: "tool_call", message: "verify", payload: {}, timestamp: "" }],
            nextRoute: "generated_project_verifier",
          }),
          graphNode("review", "waiting_review", {
            issues: [{ eventId: "issue_1", message: "schema mismatch", payload: {} }],
            routeReason: "Verifier found blocking issue.",
          }),
        ]}
        activeTab="workflow"
        activeNavId="run"
        sectionContext={{
          projectId: "project",
          task: "Reproduce",
          paperInput: "paper.pdf",
          repoInput: "",
          mode: "reproduce",
          model: "gpt-4o-mini",
          baseUrl: "",
          goal: "minimal training experiment",
          hardware: "CPU only",
          gpuInfo: "",
          mockMode: false,
          runId: "run_1",
          runStatus: "running",
          pendingActions: 0,
          eventCount: 0,
          generatedFiles: 0,
          pipelineStatus: "running",
          productGoal: "",
          targetUser: "",
        }}
        onTabChange={vi.fn()}
        onTogglePlanStep={vi.fn()}
        onApprovePlan={vi.fn()}
        onContinueRun={vi.fn()}
        onOpenRunDrawer={vi.fn()}
        onShowWorkflow={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Workflow verification summary")).toBeVisible();
    expect(screen.getByText("Verifier gates")).toBeVisible();
    expect(screen.getByText("Artifacts")).toBeVisible();
    expect(screen.getByText("Issues")).toBeVisible();
    expect(screen.getByText("Verifier found blocking issue.")).toBeVisible();
  });
});

function graphNode(
  id: string,
  status: GraphNodeData["status"],
  overrides: Partial<GraphNodeData> = {},
): GraphNodeData {
  return {
    id,
    label: id,
    agent: "",
    status,
    startedAt: "",
    finishedAt: "",
    inputArtifacts: [],
    outputArtifacts: [],
    toolCalls: [],
    issues: [],
    ...overrides,
  };
}
