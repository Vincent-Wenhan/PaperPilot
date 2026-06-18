"use client";

import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";

import { workflowEdges, workflowNodes, type WorkflowStatus } from "@/lib/mock-data";

type WorkflowNodeData = {
  label: string;
  status: WorkflowStatus;
};

const nodes: Node<WorkflowNodeData>[] = workflowNodes.map((node) => ({
  ...node,
  className: `workflow-node status-${node.data.status}`,
})) as Node<WorkflowNodeData>[];

const edges: Edge[] = workflowEdges.map((edge) => ({
  ...edge,
  animated: edge.target === "review",
  className: "workflow-edge",
}));

export function WorkflowGraph() {
  return (
    <div className="workflow-canvas" aria-label="Workflow graph">
      <ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.55} maxZoom={1.35}>
        <Background gap={18} size={1} />
        <MiniMap pannable zoomable />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
