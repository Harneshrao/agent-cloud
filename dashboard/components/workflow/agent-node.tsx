"use client";

import { memo, useEffect, useRef, useState } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { cn } from "@/lib/utils";

export type AgentNodeData = {
  label: string;
  status: "running" | "completed" | "failed" | "pending";
  executionTime?: string;
};

const statusColors = {
  running: "border-blue-500/60 bg-blue-500/10",
  completed: "border-emerald-500/60 bg-emerald-500/10",
  failed: "border-red-500/60 bg-red-500/10",
  pending: "border-border bg-card",
};

function AgentNodeComponent({ data, selected }: NodeProps<AgentNodeData>) {
  const [animating, setAnimating] = useState(false);
  const prevStatus = useRef(data.status);
  useEffect(() => {
    if (data.status !== prevStatus.current) {
      setAnimating(true);
      prevStatus.current = data.status;
      const t = setTimeout(() => setAnimating(false), 600);
      return () => clearTimeout(t);
    }
  }, [data.status]);

  const animationClass =
    animating && data.status === "running"
      ? "node-status-running"
      : animating && data.status === "completed"
        ? "node-status-completed"
        : animating && data.status === "failed"
          ? "node-status-failed"
          : "";

  return (
    <div
      className={cn(
        "rounded-2xl border-2 px-4 py-3 min-w-[160px] transition-all duration-300",
        statusColors[data.status],
        selected && "ring-2 ring-accent",
        animationClass
      )}
    >
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !border-2 !border-accent !bg-background" />
      <div className="font-medium text-foreground">{data.label}</div>
      <div className="flex items-center gap-2 mt-1">
        <span
          className={cn(
            "text-xs font-medium capitalize",
            data.status === "completed" && "text-emerald-400",
            data.status === "running" && "text-blue-400",
            data.status === "failed" && "text-red-400",
            data.status === "pending" && "text-neutral-500"
          )}
        >
          {data.status}
        </span>
        {data.executionTime && (
          <span className="text-xs text-neutral-500">{data.executionTime}</span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !border-2 !border-accent !bg-background" />
    </div>
  );
}

export const AgentNode = memo(AgentNodeComponent);
