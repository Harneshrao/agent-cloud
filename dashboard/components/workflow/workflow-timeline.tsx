"use client";

import { cn } from "@/lib/utils";
import type { WorkflowView } from "@/types";
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

interface WorkflowTimelineProps {
  workflow: WorkflowView;
  className?: string;
}

export function WorkflowTimeline({ workflow, className }: WorkflowTimelineProps) {
  const steps: { id: string; label: string; status: string; duration?: string }[] = [
    { id: "root", label: `Task #${workflow.task_id}`, status: workflow.status },
    ...workflow.child_tasks.map((c) => ({
      id: String(c.task_id),
      label: `Task #${c.task_id}`,
      status: c.status,
      duration: undefined,
    })),
  ];

  return (
    <div className={cn("space-y-0", className)}>
      <div className="text-sm font-medium text-neutral-400 mb-3">Timeline</div>
      {steps.map((step, i) => (
        <div key={step.id} className="flex gap-4">
          <div className="flex flex-col items-center">
            <div
              className={cn(
                "rounded-full p-1 transition-colors",
                step.status === "completed" && "text-emerald-500",
                step.status === "running" && "text-blue-500",
                step.status === "failed" && "text-red-500",
                step.status === "pending" && "text-neutral-500"
              )}
            >
              {step.status === "completed" && <CheckCircle2 className="h-4 w-4" />}
              {step.status === "running" && <Loader2 className="h-4 w-4 animate-spin" />}
              {step.status === "failed" && <XCircle className="h-4 w-4" />}
              {step.status === "pending" && <Circle className="h-4 w-4" />}
            </div>
            {i < steps.length - 1 && (
              <div className="w-px flex-1 min-h-[24px] bg-border mt-1" />
            )}
          </div>
          <div className="pb-6">
            <p className="font-medium text-foreground text-sm">{step.label}</p>
            <p className="text-xs text-neutral-500 capitalize mt-0.5">{step.status}</p>
            {step.duration && (
              <p className="text-xs text-neutral-400 mt-0.5">{step.duration}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
