import { describe, expect, it } from "vitest";

import {
  reduceEventsToNodes,
  type ApiEvent,
  type WorkflowNodeView,
} from "@/lib/workflow-state";

const template: WorkflowNodeView[] = [
  {
    id: "prototype",
    label: "Prototype Builder",
    agent: "Prototype Builder Agent",
    status: "pending",
    issueCount: 0,
    artifactCount: 0,
    toolCount: 0,
    routeReason: "",
  },
  {
    id: "evaluation",
    label: "Evaluator",
    agent: "Product Evaluator Agent",
    status: "pending",
    issueCount: 0,
    artifactCount: 0,
    toolCount: 0,
    routeReason: "",
  },
];

describe("workflow-state reducer", () => {
  it("reduces structured events into observable node detail", () => {
    const events: ApiEvent[] = [
      apiEvent("evt-1", "prototype", "node_started", "running", {
        input_artifacts: ["prd.md", "product_contract.json"],
        route_reason: "ProductContract accepted.",
      }),
      apiEvent("evt-2", "prototype", "tool_call", "running", {
        tool_name: "write_file",
      }),
      apiEvent("evt-3", "prototype", "artifact_created", "running", {
        path: "frontend/app.js",
      }),
      apiEvent("evt-4", "prototype", "evaluation_issue", "running", {
        issue_id: "issue-1",
      }),
      apiEvent("evt-5", "prototype", "node_finished", "success", {
        output_artifacts: ["frontend/app.js", "adapter.js"],
        next_route: "evaluation",
      }),
    ];

    const nodes = reduceEventsToNodes(template, events);
    const prototype = nodes[0];

    expect(prototype.status).toBe("success");
    expect(prototype.inputArtifacts).toEqual(["prd.md", "product_contract.json"]);
    expect(prototype.outputArtifacts).toEqual(["frontend/app.js", "adapter.js"]);
    expect(prototype.toolCount).toBe(1);
    expect(prototype.issueCount).toBe(1);
    expect(prototype.routeReason).toContain("ProductContract accepted");
    expect(prototype.nextRoute).toBe("evaluation");
  });

  it("does not mutate the template nodes between reductions", () => {
    const events = [apiEvent("evt-1", "prototype", "artifact_created", "running", { path: "a.md" })];

    reduceEventsToNodes(template, events);
    const second = reduceEventsToNodes(template, []);

    expect(second[0].artifactCount).toBe(0);
    expect(second[0].outputArtifacts).toEqual([]);
  });
});

function apiEvent(
  eventId: string,
  node: string,
  eventType: string,
  status: ApiEvent["status"],
  payload: Record<string, unknown>,
): ApiEvent {
  return {
    event_id: eventId,
    run_id: "run",
    node,
    agent: "Agent",
    event_type: eventType,
    status,
    message: eventType,
    payload,
    created_at: "2026-07-03T09:00:00Z",
  };
}
