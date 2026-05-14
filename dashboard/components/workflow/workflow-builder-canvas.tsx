"use client";

import { useCallback, useMemo, useState } from "react";
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
import { WorkflowBuilderNode, type WorkflowBuilderNodeData } from "./workflow-builder-node";
import { Button } from "@/components/ui/button";
import { createTemplate, runTemplate, fetchInstallations } from "@/lib/api";
import type { Installation } from "@/types";
import type { DagDefinition, DagNode } from "@/types";
import { cn } from "@/lib/utils";

const nodeTypes = { workflowAgent: WorkflowBuilderNode };

function nextNodeId(nodes: Node<WorkflowBuilderNodeData>[]): string {
  const ids = new Set(nodes.map((n) => n.id));
  let i = 1;
  while (ids.has(`node-${i}`)) i++;
  return `node-${i}`;
}

function flowToDag(
  nodes: Node<WorkflowBuilderNodeData>[],
  edges: Edge[]
): DagDefinition {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const depsByTarget = new Map<string, string[]>();
  for (const e of edges) {
    const target = e.target;
    if (!depsByTarget.has(target)) depsByTarget.set(target, []);
    depsByTarget.get(target)!.push(e.source);
  }
  const dagNodes: DagNode[] = nodes.map((n) => {
    const data = n.data;
    return {
      id: n.id,
      agent: data.agentName,
      task: data.taskText || `${data.agentName} step`,
      deps: depsByTarget.get(n.id) || [],
    };
  });
  return { nodes: dagNodes };
}

interface WorkflowBuilderCanvasProps {
  installations: Installation[];
}

export function WorkflowBuilderCanvas({ installations }: WorkflowBuilderCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowBuilderNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const deleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    },
    [setNodes, setEdges]
  );

  const nodeDataWithDelete = useMemo(() => {
    return nodes.map((n) => ({
      ...n,
      data: { ...n.data, onDelete: deleteNode },
    }));
  }, [nodes, deleteNode]);

  const addAgentNode = useCallback(
    (agent: Installation) => {
      const id = nextNodeId(nodes);
      const newNode: Node<WorkflowBuilderNodeData> = {
        id,
        type: "workflowAgent",
        position: { x: 250 + nodes.length * 30, y: 100 + (nodes.length % 3) * 120 },
        data: {
          label: agent.agent_name,
          agentName: agent.agent_name,
          taskText: "",
          onDelete: deleteNode,
        },
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [nodes, setNodes, deleteNode]
  );

  const updateNodeTask = useCallback(
    (nodeId: string, taskText: string) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, taskText } } : n
        )
      );
    },
    [setNodes]
  );

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node<WorkflowBuilderNodeData>) => {
    setSelectedNodeId(node.id);
  }, []);
  const onPaneClick = useCallback(() => setSelectedNodeId(null), []);

  const runWorkflow = useCallback(async () => {
    if (nodes.length === 0) {
      setMessage({ type: "error", text: "Add at least one agent to the canvas." });
      return;
    }
    setMessage(null);
    setRunning(true);
    try {
      const dag = flowToDag(nodes, edges);
      const name = `Workflow ${new Date().toISOString().slice(0, 16).replace("T", " ")}`;
      const created = await createTemplate({
        name,
        description: "Created from Workflow Builder",
        dag_definition: dag,
        visibility: "private",
      });
      const templateId = created.template?.id;
      if (templateId == null) throw new Error("Template ID missing");
      const runResult = await runTemplate(templateId, { distributed: true });
      const workflowId = runResult.workflow_id ?? runResult.root_task_ids?.[0];
      setMessage({
        type: "success",
        text: workflowId
          ? `Workflow started. Task ID: ${workflowId}. View in Workflows.`
          : "Workflow started. Check Workflows for status.",
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to run workflow";
      setMessage({
        type: "error",
        text: msg.includes("Server unavailable") ? "Server unavailable. Start the API backend to run workflows." : msg,
      });
    } finally {
      setRunning(false);
    }
  }, [nodes, edges]);

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] min-h-[520px]">
      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <p className="text-sm text-foreground-secondary">
            Add agents from the list, then connect outputs to inputs to chain steps.
          </p>
          <Button
            onClick={runWorkflow}
            disabled={running || nodes.length === 0}
            className="btn-glow"
          >
            {running ? "Starting…" : "Run workflow"}
          </Button>
        </div>
        {message && (
          <div
            className={cn(
              "rounded-xl border px-4 py-2 text-sm",
              message.type === "success"
                ? "border-success/40 bg-success/10 text-success"
                : "border-amber-200 bg-amber-50 text-amber-800"
            )}
          >
            {message.text}
          </div>
        )}
      </div>
      <div className="flex flex-1 gap-4 min-h-0 rounded-2xl border border-border bg-card/50 overflow-hidden">
        <aside className="w-56 shrink-0 border-r border-border bg-elevated/50 p-4 overflow-y-auto flex flex-col gap-4">
          <div>
            <h3 className="text-sm font-semibold text-foreground mb-3">Installed agents</h3>
            {installations.length === 0 ? (
              <p className="text-xs text-muted">No agents installed. Install from Marketplace.</p>
            ) : (
              <ul className="space-y-2">
                {installations.map((inst) => (
                  <li key={inst.installation_id}>
                    <button
                      type="button"
                      onClick={() => addAgentNode(inst)}
                      className="w-full rounded-xl border border-border bg-card px-3 py-2.5 text-left text-sm font-medium text-foreground hover:border-primary/50 hover:bg-primary-soft transition-all"
                    >
                      {inst.agent_name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {selectedNode && (
            <div className="rounded-xl border border-border bg-card p-3">
              <h3 className="text-xs font-semibold text-foreground mb-2">Task for this step</h3>
              <textarea
                value={selectedNode.data.taskText}
                onChange={(e) => updateNodeTask(selectedNode.id, e.target.value)}
                placeholder="e.g. Scrape https://example.com"
                className="w-full min-h-[80px] rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary"
                rows={3}
              />
            </div>
          )}
        </aside>
        <div className="flex-1 min-w-0">
          <ReactFlow
            nodes={nodeDataWithDelete}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            className="rounded-r-2xl"
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#1F2937" gap={16} />
            <Controls className="!border-border !bg-card !rounded-xl" />
            <MiniMap
              nodeColor="#6366F1"
              maskColor="rgba(11, 15, 25, 0.85)"
              className="!border-border !bg-card !rounded-xl"
            />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}
