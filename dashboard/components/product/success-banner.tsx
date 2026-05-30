"use client";

import { CheckCircle2 } from "lucide-react";

export function SuccessBanner({
  message,
  className,
}: {
  message: string;
  className?: string;
}) {
  return (
    <div
      className={`flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5 text-sm text-emerald-100 ${
        className ?? ""
      }`}
      role="status"
    >
      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
      <span>{message}</span>
    </div>
  );
}
