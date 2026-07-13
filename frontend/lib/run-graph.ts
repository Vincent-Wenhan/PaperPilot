/**
 * Run event → graph node enrichment.
 *
 * Pure functions extracted from WorkspaceShell so they can be unit tested
 * without rendering React.
 */

import type { RunMode, WorkflowStatus } from "@/lib/workbench-types";
import type { ApiEvent, ApiGraphNode } from "@/lib/api";

const TERMINAL_EVENT_TYPES = new Set([
  "pipeline_finished",
  "pipeline_failed",
  "proposal_executed",
  "review_actions_resolved",
]);

export function enrichGraphFromEvents(
  graph: ApiGraphNode[],
  events: ApiEvent[],
  mode: RunMode,
): ApiGraphNode[] {
  if (!graph.length || !events.length) {
    return graph;
  }
  const order = graph.map((node) => node.id);
  const indexById = new Map(order.map((id, index) => [id, index]));
  const next = graph.map((node) => ({ ...node }));
  const touched: number[] = [];
  let terminal: WorkflowStatus | null = null;
  let terminalIndex: number | null = null;
  let latestMappedNode = "";

  for (const event of events) {
    const nodeId = graphNodeFromEvent(event, mode, indexById, latestMappedNode);
    const index = nodeId ? indexById.get(nodeId) : undefined;
    if (index === undefined) {
      continue;
    }
    touched.push(index);
    if (event.event_type !== "pipeline_failed") {
      latestMappedNode = nodeId;
    }
    if (TERMINAL_EVENT_TYPES.has(event.event_type)) {
      terminal = event.status;
      terminalIndex = index;
      next[index].status = event.status;
    } else if (event.status === "running" || event.status === "waiting_review") {
      next[index].status = mergeWorkflowStatus(next[index].status, event.status);
    } else if (event.status === "success" || event.status === "failed" || event.status === "revised") {
      next[index].status = mergeWorkflowStatus(next[index].status, event.status);
    }
  }

  if (!touched.length) {
    return next;
  }
  const latest = Math.max(...touched);
  if (terminal) {
    const finalIndex = terminalIndex ?? latest;
    next.forEach((node, index) => {
      if (index < finalIndex && ["pending", "running", "waiting_review"].includes(node.status)) {
        node.status = "success";
      }
      if (index === finalIndex) {
        node.status = terminal!;
      } else if (terminal === "failed" && index > finalIndex && ["running", "waiting_review"].includes(node.status)) {
        node.status = "pending";
      }
    });
    return next;
  }
  next.forEach((node, index) => {
    if (index < latest && ["pending", "running", "waiting_review"].includes(node.status)) {
      node.status = "success";
    } else if (index === latest && node.status === "pending") {
      node.status = "running";
    }
  });
  return next;
}

function mergeWorkflowStatus(current: WorkflowStatus, incoming: WorkflowStatus): WorkflowStatus {
  if (incoming === "failed" || incoming === "success" || incoming === "revised") {
    return incoming;
  }
  if (incoming === "waiting_review") {
    return current === "failed" || current === "success" || current === "revised"
      ? current
      : incoming;
  }
  if (incoming === "running") {
    return current === "pending" ? incoming : current;
  }
  return current;
}

function graphNodeFromEvent(
  event: ApiEvent,
  mode: RunMode,
  knownNodeIds?: Map<string, number>,
  latestMappedNode = "",
): string {
  if (event.node === "run_intake" || event.node === "input_review") {
    return "parse";
  }
  if (event.node === "planner") {
    return mode === "reproduce" ? "planning" : "prd";
  }
  if (event.node === "runner_execution" || event.node === "runner_review") {
    return mode === "reproduce" ? "command_routing" : "scaffold";
  }
  if (mode === "productize" && event.event_type === "pipeline_failed") {
    return productizeErrorNode(event) || latestMappedNode || "parse";
  }
  if (
    mode === "productize" &&
    event.event_type === "pipeline_finished" &&
    event.payload?.pipeline_status === "proposal_review"
  ) {
    return "mvp";
  }
  if (mode === "productize" && event.event_type === "proposal_executed") {
    if (event.status === "failed" || event.payload?.pipeline_status === "failed") {
      return productizeErrorNode(event) || latestMappedNode || "scaffold";
    }
    return "scaffold";
  }
  if (TERMINAL_EVENT_TYPES.has(event.event_type)) {
    return mode === "reproduce" ? "outputs" : "scaffold";
  }

  const message = event.message.toLowerCase();
  if (mode === "productize") {
    if (message.includes("extracting capability")) return "capability_cards";
    if (message.includes("composing paper capabilities")) return "capability_map";
    if (message.includes("inspecting generated product")) return "scaffold";
    if (message.includes("capability card")) return "capability_cards";
    if (message.includes("capability map")) return "capability_map";
    if (message.includes("composition")) return "method_composition";
    if (message.includes("jtbd") || message.includes("job-to-be-done")) return "jtbd";
    if (message.includes("prd")) return "prd";
    if (message.includes("mvp") || message.includes("moscow")) return "mvp";
    if (message.includes("evaluation") || message.includes("evaluator")) return "evaluation";
    if (message.includes("scaffold")) return "scaffold";
    if (message.includes("selecting product template")) return "prototype";
    if (message.includes("prototype")) return "prototype";
    if (message.includes("revision")) return "revision";
  }

  if (knownNodeIds?.has(event.node)) {
    return event.node;
  }

  if (message.includes("research understanding")) return "research_evidence";
  if (message.includes("repository cloner") || message.includes("repository understanding")) return "repo_evidence";
  if (message.includes("reproduction planner")) return "planning";
  if (message.includes("implementation agent") || message.includes("generating code") || message.includes("revising code")) return "implementation";
  if (message.includes("sandbox")) return "command_routing";
  if (message.includes("code review") || message.includes("second review") || message.includes("review verdict")) return "review";
  if (message.includes("execution") || message.includes("diagnosis")) return "diagnosis";
  if (message.includes("report") || message.includes("output")) return "outputs";
  return event.node;
}

function productizeErrorNode(event: ApiEvent): string {
  const errors = event.payload?.errors;
  if (!Array.isArray(errors)) {
    return "";
  }
  const text = errors.map((error) => String(error).toLowerCase()).join(" ");
  if (text.includes("prototype builder agent")) return "prototype";
  if (text.includes("product evaluator agent")) return "evaluation";
  if (text.includes("product planner agent")) return "prd";
  if (text.includes("research synthesizer agent")) return "capability_cards";
  if (text.includes("scaffold")) return "scaffold";
  return "";
}
