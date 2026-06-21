import React from "react";
import { render, screen, within } from "@testing-library/react";
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

  it("exposes clickable local workbench navigation", async () => {
    const onNavSelect = vi.fn();
    render(
      <ProjectSidebar
        currentTask="LLM Compiler Design"
        query=""
        selectedNavId="paper"
        visibleNavItems={projectNavItems}
        onQueryChange={vi.fn()}
        onNavSelect={onNavSelect}
        onNewRun={vi.fn()}
      />,
    );

    expect(screen.getByRole("navigation", { name: "Project navigation" })).toBeVisible();
    for (const label of ["Projects", "Papers", "Repos", "Runs", "Agents", "Settings"]) {
      expect(screen.getByRole("button", { name: label })).toBeVisible();
    }
    expect(screen.getByText("PaperPilot")).toBeVisible();
    expect(screen.getByText("Local Workbench")).toBeVisible();
    expect(screen.queryByText("Pro Plan")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Repos" }));
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));

    expect(onNavSelect).toHaveBeenCalledWith("repo");
    expect(onNavSelect).toHaveBeenCalledWith("settings");
  });

  it("shows project context, run state, and the primary command", () => {
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
    expect(screen.queryByRole("button", { name: "Messages" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New Run" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "New run options" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Local workspace session" })).toBeVisible();
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

  it("keeps the selected generated file across inspector refreshes", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/artifacts/run_current")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/api/files/run_current")) {
        return jsonResponse([
          { path: "README.md", name: "README.md", kind: "file", size_bytes: 10 },
          { path: "main.py", name: "main.py", kind: "file", size_bytes: 10 },
        ]);
      }
      if (url.includes("/api/files/run_current/content")) {
        const parsed = new URL(url);
        const path = parsed.searchParams.get("path");
        return jsonResponse({
          path,
          content: path === "main.py" ? "print('current')" : "# Current",
          truncated: false,
        });
      }
      if (url.endsWith("/api/patches/run_current") || url.endsWith("/api/runs/run_current/actions")) {
        return jsonResponse([]);
      }
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(
      <InspectorPanel runId="run_current" events={[]} preview={false} refreshToken="1" />,
    );

    expect(
      await within(await screen.findByLabelText("Code viewer")).findByText("README.md"),
    ).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "main.py" }));
    expect(
      await within(await screen.findByLabelText("Code viewer")).findByText("main.py"),
    ).toBeVisible();

    rerender(<InspectorPanel runId="run_current" events={[]} preview={false} refreshToken="2" />);

    const viewer = await screen.findByLabelText("Code viewer");
    expect(await within(viewer).findByText("main.py")).toBeVisible();
    expect(within(viewer).getByText("print('current')")).toBeVisible();
  });

  it("keeps the console visible with live controls and tab switching", async () => {
    render(<BottomDock events={agentEvents} commandResults="python main.py --help" />);

    expect(screen.getByRole("region", { name: "Run console" })).toBeVisible();
    expect(screen.getByLabelText("Live")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
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
    expect(screen.getByRole("button", { name: "Approve & Execute" })).toBeVisible();
  });

  it("saves command edits without approving execution", async () => {
    const onApprove = vi.fn();
    const onEdit = vi.fn();
    render(
      <ActionApprovalDrawer
        open
        actions={[
          {
            id: "action_1",
            runId: "run_demo",
            agent: "Runner",
            type: "run_command",
            risk: "safe",
            reason: "Check Python",
            payload: { command: "python --version" },
            status: "pending",
          },
        ]}
        onClose={vi.fn()}
        onApprove={onApprove}
        onEdit={onEdit}
        onReject={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    const editor = screen.getByLabelText("Command");
    await userEvent.clear(editor);
    await userEvent.type(editor, "python main.py --help");
    await userEvent.click(screen.getByRole("button", { name: "Save Edit" }));

    expect(onEdit).toHaveBeenCalledWith("action_1", "python main.py --help");
    expect(onApprove).not.toHaveBeenCalled();
  });
});

function jsonResponse(body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}
