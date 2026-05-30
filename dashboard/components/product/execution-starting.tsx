"use client";

import { Loader2 } from "lucide-react";
import { SUCCESS_MESSAGES } from "@/lib/trust-copy";

export function ExecutionStarting() {
  return (
    <div
      className="flex items-center gap-3 rounded-lg border border-primary/15 bg-primary/5 px-4 py-3"
      role="status"
      aria-live="polite"
    >
      <Loader2 className="h-5 w-5 shrink-0 animate-spin text-primary" />
      <div>
        <p className="text-sm font-medium text-foreground">Execution starting</p>
        <p className="text-xs text-neutral-500">{SUCCESS_MESSAGES.taskStarting}</p>
      </div>
    </div>
  );
}
