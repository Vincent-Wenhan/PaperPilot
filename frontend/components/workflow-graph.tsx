"use client";

import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { CheckCircle2, Circle, Clock3, LoaderCircle } from "lucide-react";
import { useCallback, useState } from "react";

import type { WorkflowStatus } from "@/lib/workbench-types";

export type GraphNodeData = {
  id: string;
  label: string;
  agent: string;
  status: WorkflowStatus;
  startedAt: string;
  finishedAt: string;
  inputArtifacts: string[];
  outputArtifacts: string[];
  toolCalls: Array<{
    eventId: string;
    type: string;
    message: string;
    payload: Record<string, unknown>;
    timestamp: string;
  }>;
  issues: Array<{
    eventId: string;
    message: string;
    payload: Record<string, unknown>;
  }>;
};

type WorkflowGraphProps = {
  nodes?: GraphNodeData[];
  edges?: Array<{ id: string; source: string; target: string }>;
};

const DEFAULT_LAYOUT: Record<string, { x: number; y: number }> = {
  parse: { x: 20, y: 20 },
  research_evidence: { x: 220, y: 20 },
  repo_evidence: { x: 220, y: 20 },
  planning: { x: 420, y: 20 },
  command_routing: { x: 620, y: 20 },
  implementation: { x: 620, y: 20 },
  review: { x: 100, y: 170 },
  evaluation: { x: 100, y: 170 },
  revision: { x: 360, y: 170 },
  diagnosis: { x: 360, y: 170 },
  outputs: { x: 620, y: 170 },
  capability_cards: { x: 20, y: 20 },
  capability_map: { x: 220, y: 20 },
  method_composition: { x: 420, y: 20 },
  jtbd: { x: 620, y: 20 },
  prd: { x: 100, y: 170 },
  mvp: { x: 360, y: 170 },
  prototype: { x: 620, y: 170 },
  scaffold: { x: 620, y: 170 },
};

const FALLBACK_NODES: GraphNodeData[] = [];

function computeEdges(nodeIds: string[]): Array<{ id: string; source: string; target: string }> {
  const edges: Array<{ id: string; source: string; target: string }> = [];
  for (let i = 0; i < nodeIds.length - 1; i++) {
    edges.push({
      id: `edge-${nodeIds[i]}-${nodeIds[i + 1]}`,
      source: nodeIds[i],
      target: nodeIds[i + 1],
    });
  }
  return edges;
}

function WorkflowNodeCard({ data }: NodeProps) {
  const nodeData = data as unknown as GraphNodeData;
  const toolCount = nodeData.toolCalls?.length ?? 0;
  const issueCount = nodeData.issues?.length ?? 0;
  const StatusIcon = nodeData.status === "success" ? CheckCircle2 : nodeData.status === "running" ? LoaderCircle : nodeData.status === "waiting_review" ? Clock3 : Circle;
  return (
    <div className={`workflow-node-card status-${nodeData.status}`}>
      <Handle className="workflow-node-handle" position={Position.Left} type="target" />
      <div className="node-title"><StatusIcon size={17} /><strong>{nodeData.label}</strong></div>
      <div className="node-status-row">
        <span>{nodeData.status === "success" ? "Completed" : nodeData.status === "waiting_review" ? "Review" : nodeData.status}</span>
        <time>{nodeData.finishedAt}</time>
      </div>
      <div className="node-meta">
        {toolCount > 0 && <span className="node-badge">{toolCount} tools</span>}
        {issueCount > 0 && <span className="node-badge issue">{issueCount} issues</span>}
      </div>
      <Handle className="workflow-node-handle" position={Position.Right} type="source" />
    </div>
  );
}

const nodeTypes = { workflowNode: WorkflowNodeCard };

export function WorkflowGraph({ nodes: graphNodes, edges: graphEdges }: WorkflowGraphProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const data = graphNodes?.find((n) => n.id === node.id);
      setSelectedNode(data ?? null);
    },
    [graphNodes],
  );

  const displayNodes = graphNodes && graphNodes.length > 0 ? graphNodes : FALLBACK_NODES;
  const compiledNodes: Node[] = (displayNodes
  ).map((gn) => {
    const pos = DEFAULT_LAYOUT[gn.id] ?? { x: 0, y: 0 };
    return {
      id: gn.id,
      type: "workflowNode",
      position: pos,
      data: gn,
      className: `workflow-node status-${gn.status}`,
    };
  });

  const compiledEdges: Edge[] = (graphEdges && graphEdges.length > 0
    ? graphEdges
    : computeEdges(displayNodes.map((n) => n.id))
  ).map((edge) => ({
    ...edge,
    type: "smoothstep",
    animated: edge.target === "review" || edge.target === "revision",
    className: "workflow-edge",
  }));

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div className="workflow-canvas" aria-label="Workflow graph" style={{ flex: 1 }}>
        <ReactFlow
          nodes={compiledNodes}
          edges={compiledEdges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.18, minZoom: 0.55, maxZoom: 0.9 }}
          minZoom={0.55}
          maxZoom={1.35}
          nodesDraggable={false}
          nodesConnectable={false}
        >
          <Background gap={18} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      {selectedNode && <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />}
    </div>
  );
}

function NodeDetailPanel({
  node,
  onClose,
}: {
  node: GraphNodeData;
  onClose: () => void;
}) {
  return (
    <div className="node-detail-panel" style={{ maxHeight: 240, overflow: "auto", borderTop: "1px solid var(--border)", padding: "12px 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>{node.label}</h3>
        <button className="icon-button" type="button" onClick={onClose} title="Close">
          ✕
        </button>
      </div>
      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 12px", marginTop: 8 }}>
        <dt>Agent</dt>
        <dd>{node.agent}</dd>
        <dt>Status</dt>
        <dd>{node.status}</dd>
        {node.startedAt && (<><dt>Started</dt><dd>{node.startedAt}</dd></>)}
        {node.finishedAt && (<><dt>Finished</dt><dd>{node.finishedAt}</dd></>)}
        {node.inputArtifacts.length > 0 && (
          <><dt>Inputs</dt><dd>{node.inputArtifacts.join(", ")}</dd></>
        )}
        {node.outputArtifacts.length > 0 && (
          <><dt>Outputs</dt><dd>{node.outputArtifacts.join(", ")}</dd></>
        )}
        {node.toolCalls.length > 0 && (
          <><dt>Tool Calls</dt><dd>{node.toolCalls.map((tc) => tc.message).join("; ")}</dd></>
        )}
        {node.issues.length > 0 && (
          <><dt>Issues</dt><dd>{node.issues.map((i) => i.message).join("; ")}</dd></>
        )}
      </dl>
    </div>
  );
}
