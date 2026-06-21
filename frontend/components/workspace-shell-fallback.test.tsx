import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceShell } from "@/components/workspace-shell";

vi.mock("@/components/workflow-graph", () => ({
  WorkflowGraph: () => <div aria-label="Workflow graph" />,
}));

vi.mock("@/components/inspector-panel", () => ({
  InspectorPanel: () => <aside aria-label="Run inspector" />,
}));

describe("workspace demo fallback", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  });

  it("shows an honest empty state when the backend is unavailable", async () => {
    render(<WorkspaceShell />);

    expect(await screen.findByText(/No backend run yet/)).toBeVisible();
    expect(screen.getByText(/No events yet/)).toBeVisible();
    expect(screen.queryByRole("complementary", { name: "Approval Required" })).not.toBeInTheDocument();
  });

  it("switches the center workspace when sidebar navigation is clicked", async () => {
    render(<WorkspaceShell />);

    await userEvent.click(screen.getByRole("button", { name: "Repos" }));
    const repoPanel = await screen.findByRole("region", { name: "Repository Input" });
    expect(repoPanel).toBeVisible();
    expect(within(repoPanel).getByRole("heading", { name: "Repository Input" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Open Workflow" }));
    expect(await screen.findByLabelText("Workflow graph panel")).toBeVisible();
  });

  it("approves real actions through the execute endpoint and refreshes state", async () => {
    const run = {
      run_id: "run_real",
      project_id: "project_real",
      mode: "reproduce",
      status: "running",
      task: "Run real action",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      summary: "Waiting for approval.",
      inputs: { pdf_path: "uploads/paper.pdf", llm_model: "gpt-4o-mini" },
      result_summary: {},
      plan: ["Review bounded command"],
    };
    const pendingAction = {
      action_id: "act_execute",
      run_id: "run_real",
      agent: "Reproduction Planner Agent",
      tool: "run_command",
      command: "python --version",
      cwd: ".",
      execution_mode: "safe",
      patch_id: "",
      path: "",
      risk: "low",
      reason: "Version check",
      status: "pending",
      edited_command: "",
      execution_status: "not_started",
      execution_result: {},
    };
    const executedAction = {
      ...pendingAction,
      status: "approved",
      execution_status: "succeeded",
      execution_result: {
        command: "python --version",
        cwd: ".",
        mode: "safe",
        executed: true,
        risk_level: "low",
        exit_code: 0,
        stdout: "Python 3.12",
        stderr: "",
        blocked_reason: null,
      },
    };
    let executed = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/llm/config")) {
        return jsonResponse({ api_key: "", base_url: "", model: "gpt-4o-mini", implementation_model: "" });
      }
      if (url.endsWith("/api/runs/run_real")) {
        return jsonResponse(run);
      }
      if (url.endsWith("/api/runs/run_real/events")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/api/runs/run_real/graph")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/api/runs/run_real/actions")) {
        return jsonResponse([executed ? executedAction : pendingAction]);
      }
      if (url.endsWith("/api/commands/run_real/result")) {
        return jsonResponse(executed ? [executedAction.execution_result] : []);
      }
      if (url.endsWith("/api/runs/run_real/result")) {
        return jsonResponse({ pipeline_status: "complete" });
      }
      if (url.endsWith("/api/actions/act_execute/execute") && init?.method === "POST") {
        executed = true;
        return jsonResponse({
          action: executedAction,
          message: "Command completed successfully.",
          execution_status: "succeeded",
          command_result: executedAction.execution_result,
          patch_result: null,
          blocked_reason: null,
        });
      }
      return jsonResponse({});
    });
    window.sessionStorage.setItem("paperpilot.activeRunId", "run_real");
    vi.stubGlobal("fetch", fetchMock);

    render(<WorkspaceShell />);

    await userEvent.click(await screen.findByRole("button", { name: "Approve & Execute" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/api/actions/act_execute/execute",
        { method: "POST" },
      );
    });
    await waitFor(() => {
      expect(screen.queryByRole("complementary", { name: "Approval Required" })).not.toBeInTheDocument();
    });
  });

  it("does not restore legacy active runs from localStorage", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({}));
    window.localStorage.setItem("paperpilot.activeRunId", "run_legacy");
    vi.stubGlobal("fetch", fetchMock);

    render(<WorkspaceShell />);

    expect(await screen.findByText(/No backend run yet/)).toBeVisible();
    expect(window.localStorage.getItem("paperpilot.activeRunId")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "http://localhost:8000/api/runs/run_legacy",
      expect.anything(),
    );
  });

  it("does not restore non-running runs from sessionStorage", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/llm/config")) {
        return jsonResponse({ api_key: "", base_url: "", model: "gpt-4o-mini", implementation_model: "" });
      }
      if (url.endsWith("/api/runs/run_review")) {
        return jsonResponse({
          run_id: "run_review",
          project_id: "project_real",
          mode: "reproduce",
          status: "waiting_review",
          task: "Old review run",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          summary: "Waiting for review.",
          inputs: { pdf_path: "uploads/paper.pdf", llm_model: "gpt-4o-mini" },
          result_summary: {},
          plan: ["Review bounded command"],
        });
      }
      if (
        url.endsWith("/api/runs/run_review/events") ||
        url.endsWith("/api/runs/run_review/graph") ||
        url.endsWith("/api/runs/run_review/actions") ||
        url.endsWith("/api/commands/run_review/result")
      ) {
        return jsonResponse([]);
      }
      if (url.endsWith("/api/runs/run_review/result")) {
        return jsonResponse({ pipeline_status: "waiting_review" });
      }
      return jsonResponse({});
    });
    window.sessionStorage.setItem("paperpilot.activeRunId", "run_review");
    vi.stubGlobal("fetch", fetchMock);

    render(<WorkspaceShell />);

    expect((await screen.findAllByText(/Previous run run_review is not running anymore/)).length).toBeGreaterThan(0);
    expect(screen.getByText(/No backend run yet/)).toBeVisible();
    expect(window.sessionStorage.getItem("paperpilot.activeRunId")).toBeNull();
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
