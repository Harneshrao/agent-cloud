"use client";

import { useCallback, useEffect, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { AgentNode, type AgentNodeData } from "./agent-node";
import type { WorkflowView } from "@/types";

const nodeTypes = { agent: AgentNode };

function workflowToNodesAndEdges(view: WorkflowView): { nodes: Node<AgentNodeData>[]; edges: Edge[] } {
  const nodes: Node<AgentNodeData>[] = [];
  const edges: Edge[] = [];
  const rootId = `task-${view.task_id}`;
  nodes.push({
    id: rootId,
    type: "agent",
    position: { x: 200, y: 0 },
    data: {
      label: `Task #${view.task_id}`,
      status: (view.status as AgentNodeData["status"]) || "pending",
    },
  });
  view.child_tasks.forEach((child, i) => {
    const childId = `task-${child.task_id}`;
    nodes.push({
      id: childId,
      type: "agent",
      position: { x: 100 + i * 220, y: 120 },
      data: {
        label: `Task #${child.task_id}`,
        status: (child.status as AgentNodeData["status"]) || "pending",
      },
    });
    edges.push({
      id: `e-${view.task_id}-${child.task_id}`,
      source: rootId,
      target: childId,
      animated: view.status === "running" || child.status === "running",
      style: { stroke: view.status === "running" ? "#6366f1" : undefined },
    });
  });
  return { nodes, edges };
}

interface FlowViewProps {
  workflow: WorkflowView;
}

export function FlowView({ workflow }: FlowViewProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => workflowToNodesAndEdges(workflow),
    [workflow]
  );
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <div className="h-[500px] w-full rounded-2xl border border-border bg-card/50 transition-shadow duration-300 hover:shadow-soft">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        className="rounded-2xl"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#2a2a2a" gap={16} />
        <Controls className="!border-border !bg-card !rounded-xl" />
        <MiniMap
          nodeColor="#6366f1"
          maskColor="rgba(15,15,15,0.8)"
          className="!border-border !bg-card !rounded-xl"
        />
      </ReactFlow>
    </div>
  );
}
