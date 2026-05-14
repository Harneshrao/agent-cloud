"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-xl border border-border bg-card p-8 text-center shadow-soft",
        className
      )}
    >
      <div className="text-muted [&>svg]:h-12 [&>svg]:w-12">{icon}</div>
      <div className="grid gap-4">
        <h3 className="text-lg font-medium text-foreground">{title}</h3>
      {description && (
          <p className="max-w-sm text-sm text-foreground-secondary">{description}</p>
      )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
