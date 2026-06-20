import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InspectorPanel } from "@/components/inspector-panel";
import { ActionApprovalDrawer } from "@/components/approval/action-approval-drawer";
import { BottomDock } from "@/components/layout/bottom-dock";
import { ProjectSidebar } from "@/components/layout/project-sidebar";
import { TopBar } from "@/components/layout/top-bar";
import { agentEvents, projectNavItems } from "@/lib/mock-data";

vi.mock("@/components/code/code-editor", () => ({
  CodeEditor: ({ file }: { file: { path: string; content: string } }) => (
    <section aria-label="Code viewer">
      <strong>{file.path}</strong>
      <pre>{file.content}</pre>
    </section>
  ),
}));

describe("reference workbench layout", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  });

  it("exposes the reference global navigation", () => {
    render(
      <ProjectSidebar
        currentTask="LLM Compiler Design"
        query=""
        selectedNavId="paper"
        visibleNavItems={projectNavItems}
        onQueryChange={vi.fn()}
        onNavSelect={vi.fn()}
        onNewRun={vi.fn()}
      />,
    );

    expect(screen.getByRole("navigation", { name: "Project navigation" })).toBeVisible();
    for (const label of ["Projects", "Papers", "Repos", "Runs", "Agents", "Settings"]) {
      expect(screen.getByRole("button", { name: label })).toBeVisible();
    }
    expect(screen.getByText("PaperPilot")).toBeVisible();
    expect(screen.getByText("Pro Plan")).toBeVisible();
  });

  it("shows project context, run state, messages, and the primary command", () => {
    render(
      <TopBar
        run={{
          projectName: "LLM Compiler Design",
          runId: "Run #23",
          mode: "productize",
          status: "running",
          elapsed: "00:06:42",
        }}
        onNewRun={vi.fn()}
      />,
    );

    expect(screen.getByText("LLM Compiler Design")).toBeVisible();
    expect(screen.getByText("Run #23")).toBeVisible();
    expect(screen.getByRole("button", { name: "Messages" })).toBeVisible();
    expect(screen.getByRole("button", { name: "New Run" })).toBeVisible();
  });

  it("opens the inspector on Code and keeps the reference tab set", async () => {
    render(<InspectorPanel runId="run_demo" events={agentEvents} />);

    expect(screen.getByText("Files")).toBeVisible();
    expect(screen.getByRole("tab", { name: "Code" })).toHaveAttribute("aria-selected", "true");
    for (const label of ["Artifacts", "Diff", "Runner", "Tool Calls"]) {
      expect(screen.getByRole("tab", { name: label })).toBeVisible();
    }

    await userEvent.click(screen.getByRole("tab", { name: "Artifacts" }));
    expect(screen.getByText("reproduction_plan.md")).toBeVisible();
  });

  it("keeps the console visible with live controls and tab switching", async () => {
    render(<BottomDock events={agentEvents} commandResults="python main.py --help" />);

    expect(screen.getByRole("region", { name: "Run console" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Live" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Pause" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Clear" })).toBeVisible();

    await userEvent.click(screen.getByRole("tab", { name: "Terminal" }));
    expect(screen.getByText("python main.py --help")).toBeVisible();
  });

  it("renders review-required actions as the floating approval panel", () => {
    render(
      <ActionApprovalDrawer
        open
        actions={[
          {
            id: "action_1",
            runId: "run_demo",
            agent: "Prototype Builder",
            type: "apply_patch",
            risk: "review",
            reason: "Implement prototype scaffold and API endpoints.",
            payload: { command: "git apply prototype.patch" },
            status: "pending",
          },
        ]}
        onClose={vi.fn()}
        onApprove={vi.fn()}
        onEdit={vi.fn()}
        onReject={vi.fn()}
      />,
    );

    expect(screen.getByRole("complementary", { name: "Approval Required" })).toBeVisible();
    expect(screen.getByText("git apply prototype.patch")).toBeVisible();
    expect(screen.getByRole("button", { name: "Approve" })).toBeVisible();
  });
});
