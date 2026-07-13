import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceShell } from "@/components/workspace-shell";
import { enrichGraphFromEvents } from "@/lib/run-graph";

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

  it("appends productize PDF uploads and submits all selected paths", async () => {
    let createdRunBody: Record<string, unknown> | null = null;
    let executedProposalIndex: number | null = null;
    const proposals = [
      {
        product_name: "Proposal A",
        target_user: "Students",
        product_goal: "Demo",
        jtbd: "Review research",
        prd: { core_features: ["Compare methods"] },
        risks: ["Mock only"],
      },
      {
        product_name: "Proposal B",
        target_user: "Researchers",
        product_goal: "Prototype",
        jtbd: "Inspect capabilities",
        prd: { core_features: ["Trace evidence"] },
        risks: ["Requires manual adapter review"],
      },
    ];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/llm/config")) {
        return jsonResponse({ api_key: "", base_url: "", model: "gpt-4o-mini", implementation_model: "" });
      }
      if (url.endsWith("/api/upload/pdf") && init?.method === "POST") {
        const callCount = fetchMock.mock.calls.filter(([calledUrl]) =>
          String(calledUrl).endsWith("/api/upload/pdf"),
        ).length;
        return jsonResponse({ pdf_path: `uploads/paper-${callCount}.pdf` });
      }
      if (url.endsWith("/api/runs") && init?.method === "POST") {
        createdRunBody = JSON.parse(String(init.body));
        return jsonResponse({
          run_id: "run_productize",
          project_id: "paperpilot_workspace",
          mode: "productize",
          status: "waiting_review",
          task: "Productize the submitted research into a mock-first MVP.",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          summary: "Productize proposals ready.",
          inputs: {
            pdf_path: "uploads/paper-1.pdf",
            pdf_paths: "uploads/paper-1.pdf\nuploads/paper-2.pdf",
            llm_model: "gpt-4o-mini",
          },
          result_summary: { pipeline_status: "proposal_review" },
          plan: ["Generate product proposals"],
        });
      }
      if (url.endsWith("/api/runs/run_productize")) {
        return jsonResponse({
          run_id: "run_productize",
          project_id: "paperpilot_workspace",
          mode: "productize",
          status: executedProposalIndex === null ? "waiting_review" : "success",
          task: "Productize the submitted research into a mock-first MVP.",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          summary:
            executedProposalIndex === null
              ? "Productize proposals ready."
              : "Selected product proposal executed.",
          inputs: {
            pdf_path: "uploads/paper-1.pdf",
            pdf_paths: "uploads/paper-1.pdf\nuploads/paper-2.pdf",
            llm_model: "gpt-4o-mini",
          },
          result_summary: {
            pipeline_status:
              executedProposalIndex === null ? "proposal_review" : "complete",
          },
          plan: ["Generate product proposals"],
        });
      }
      if (
        url.endsWith("/api/runs/run_productize/events") ||
        url.endsWith("/api/runs/run_productize/graph") ||
        url.endsWith("/api/runs/run_productize/actions") ||
        url.endsWith("/api/commands/run_productize/result")
      ) {
        return jsonResponse([]);
      }
      if (url.endsWith("/api/runs/run_productize/result")) {
        return jsonResponse({
          pipeline_status: "proposal_review",
          productize_stage: "proposal_review",
          productize_proposals: proposals,
          selected_proposal:
            executedProposalIndex === null
              ? undefined
              : proposals[executedProposalIndex],
          generated_files: executedProposalIndex === null ? 0 : 4,
        });
      }
      if (url.endsWith("/api/runs/run_productize/productize/proposals/1/execute") && init?.method === "POST") {
        executedProposalIndex = 1;
        return jsonResponse({
          pipeline_status: "complete",
          productize_stage: "executed",
          productize_proposals: proposals,
          selected_proposal: proposals[1],
          generated_files: 4,
        });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<WorkspaceShell />);
    const user = userEvent.setup();

    await user.selectOptions(
      await screen.findByLabelText("Workbench mode"),
      "productize",
    );
    await user.click(screen.getByRole("button", { name: "New Run" }));
    expect(await screen.findByRole("heading", { name: "New Run" })).toBeVisible();

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();
    expect(fileInput.multiple).toBe(true);

    await user.upload(fileInput, new File(["one"], "one.pdf", { type: "application/pdf" }));
    await screen.findByRole("button", { name: /one.pdf/ });
    await user.upload(fileInput, new File(["two"], "two.pdf", { type: "application/pdf" }));
    await screen.findByText(/2 PDFs selected/);

    await user.click(screen.getByRole("button", { name: "Run Agents" }));

    await waitFor(() => {
      expect(createdRunBody?.pdf_paths).toEqual([
        "uploads/paper-1.pdf",
        "uploads/paper-2.pdf",
      ]);
    });
    expect(await screen.findByRole("heading", { name: "Choose a Product Proposal" })).toBeVisible();
    expect(screen.getByText(/Review the proposal options below/)).toBeVisible();
    expect(screen.getByText("Trace evidence")).toBeVisible();
    expect(screen.getAllByRole("button", { name: "Select & Scaffold Proposal" })).toHaveLength(2);

    await user.click(screen.getAllByRole("button", { name: "Select & Scaffold Proposal" })[1]);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/api/runs/run_productize/productize/proposals/1/execute",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: expect.any(String),
        }),
      );
    });
    const executeCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/api/runs/run_productize/productize/proposals/1/execute"),
    );
    expect(JSON.parse(String(executeCall?.[1]?.body))).toMatchObject({
      base_url: "https://api.openai.com/v1",
      model: "gpt-4o-mini",
      mock_mode: false,
    });
    expect(await screen.findByText("Selected proposal")).toBeVisible();
    expect(screen.getByText("Proposal B")).toBeVisible();
  });

  it("keeps outputs successful after reviewed actions resolve", () => {
    const graph = [
      graphNode("parse", "success"),
      graphNode("planning", "success"),
      graphNode("command_routing", "success"),
      graphNode("outputs", "success"),
    ];
    const events = [
      apiEvent("evt_pipeline", "agent_runtime", "pipeline_finished", "waiting_review"),
      apiEvent("evt_execute", "runner_execution", "action_execution_succeeded", "success"),
      apiEvent("evt_resolved", "outputs", "review_actions_resolved", "success"),
    ];

    const enriched = enrichGraphFromEvents(graph as never, events as never, "reproduce");

    expect(enriched.find((node) => node.id === "outputs")?.status).toBe("success");
  });

  it("keeps productize proposal review on planning nodes until a proposal is executed", () => {
    const graph = [
      graphNode("parse", "success"),
      graphNode("capability_cards", "success"),
      graphNode("capability_map", "success"),
      graphNode("method_composition", "success"),
      graphNode("jtbd", "success"),
      graphNode("prd", "waiting_review"),
      graphNode("mvp", "pending"),
      graphNode("prototype", "pending"),
      graphNode("evaluation", "pending"),
      graphNode("revision", "pending"),
      graphNode("scaffold", "pending"),
    ];
    const events = [
      apiEvent("evt_parse", "parse", "node_started", "running"),
      apiEvent("evt_prd", "prd", "node_started", "running"),
      {
        ...apiEvent("evt_review", "agent_runtime", "pipeline_finished", "waiting_review"),
        payload: { pipeline_status: "proposal_review" },
      },
    ];

    const enriched = enrichGraphFromEvents(graph as never, events as never, "productize");

    expect(enriched.find((node) => node.id === "prd")?.status).toBe("success");
    expect(enriched.find((node) => node.id === "mvp")?.status).toBe("waiting_review");
    expect(enriched.find((node) => node.id === "prototype")?.status).toBe("pending");
    expect(enriched.find((node) => node.id === "evaluation")?.status).toBe("pending");
    expect(enriched.find((node) => node.id === "revision")?.status).toBe("pending");
    expect(enriched.find((node) => node.id === "scaffold")?.status).toBe("pending");
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

function graphNode(id: string, status: string) {
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
  };
}

function apiEvent(
  event_id: string,
  node: string,
  event_type: string,
  status: string,
) {
  return {
    event_id,
    run_id: "run_real",
    node,
    agent: "Workbench",
    event_type,
    status,
    message: "",
    payload: {},
    created_at: new Date().toISOString(),
  };
}
