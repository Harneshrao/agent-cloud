"use client";

import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, Loader2, Clock } from "lucide-react";

const statusConfig: Record<
  string,
  { label: string; className: string; icon: React.ElementType }
> = {
  completed: {
    label: "Completed",
    className: "bg-success/10 text-success border-success/20",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "bg-error/10 text-error border-error/20",
    icon: XCircle,
  },
  running: {
    label: "Running",
    className: "bg-warning/10 text-warning border-warning/20",
    icon: Loader2,
  },
  pending: {
    label: "Pending",
    className: "bg-muted/20 text-foreground-secondary border-border",
    icon: Clock,
  },
};

export function RunStatusBadge({ status }: { status: string }) {
  const config = statusConfig[status?.toLowerCase()] ?? statusConfig.pending;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        config.className
      )}
    >
      {status?.toLowerCase() === "running" ? (
        <Icon className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Icon className="h-3.5 w-3.5" />
      )}
      {config.label}
    </span>
  );
}
