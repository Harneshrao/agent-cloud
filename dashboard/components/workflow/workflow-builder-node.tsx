"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { cn } from "@/lib/utils";
import { Trash2 } from "lucide-react";

export type WorkflowBuilderNodeData = {
  label: string;
  agentName: string;
  taskText: string;
  onDelete?: (nodeId: string) => void;
};

function WorkflowBuilderNodeComponent({
  id,
  data,
  selected,
}: NodeProps<WorkflowBuilderNodeData>) {
  return (
    <div
      className={cn(
        "rounded-2xl border-2 min-w-[200px] max-w-[260px] transition-all duration-200",
        "border-border bg-card hover:border-primary/50",
        selected && "ring-2 ring-primary border-primary/60"
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !border-2 !border-primary !bg-background"
      />
      <div className="px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="font-semibold text-foreground truncate" title={data.agentName}>
              {data.label || data.agentName}
            </div>
            {data.taskText ? (
              <p className="text-xs text-foreground-secondary mt-1 line-clamp-2" title={data.taskText}>
                {data.taskText}
              </p>
            ) : (
              <p className="text-xs text-muted mt-1 italic">No task text</p>
            )}
          </div>
          {data.onDelete && (
            <button
              type="button"
              aria-label="Remove node"
              onClick={() => data.onDelete?.(id)}
              className="shrink-0 rounded-lg p-1.5 text-muted hover:bg-elevated hover:text-error transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !border-2 !border-primary !bg-background"
      />
    </div>
  );
}

export const WorkflowBuilderNode = memo(WorkflowBuilderNodeComponent);
