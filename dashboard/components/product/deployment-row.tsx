"use client";

import Link from "next/link";
import { PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  deploymentStatusLabel,
  deploymentStatusTone,
} from "@/lib/trust-copy";
import type { DeploymentRecord } from "@/types";

export function DeploymentRow({
  deployment,
  highlighted,
  running,
  onRun,
  onRollback,
}: {
  deployment: DeploymentRecord;
  highlighted?: boolean;
  running: boolean;
  onRun: () => void;
  onRollback: () => void;
}) {
  const tone = deploymentStatusTone(deployment.status);
  const isActive = deployment.status === "active";

  const statusClass =
    tone === "ready"
      ? "text-emerald-400"
      : tone === "attention"
        ? "text-amber-400"
        : "text-neutral-400";

  return (
    <li
      className={`flex flex-wrap items-center justify-between gap-4 px-6 py-4 ${
        highlighted ? "bg-primary/5" : ""
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="font-medium text-foreground">
          {deployment.agent_name}{" "}
          <span className="text-neutral-500">v{deployment.version}</span>
        </div>
        <p className={`mt-0.5 text-sm ${statusClass}`}>
          {deploymentStatusLabel(deployment.status)}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {isActive ? (
          <Button
            type="button"
            size="sm"
            disabled={running}
            onClick={onRun}
          >
            <PlayCircle className="mr-1.5 h-4 w-4" />
            {running ? "Running…" : "Run task"}
          </Button>
        ) : (
          <span className="text-xs text-neutral-500">Fix status before running</span>
        )}
        <Link
          href="/runs"
          className="rounded-lg px-3 py-1.5 text-sm text-neutral-400 hover:bg-white/5 hover:text-foreground"
        >
          Runs
        </Link>
        <button
          type="button"
          className="rounded-lg px-3 py-1.5 text-sm text-neutral-500 hover:bg-white/5 hover:text-neutral-300 disabled:opacity-40"
          disabled={running}
          onClick={onRollback}
        >
          Restore previous
        </button>
      </div>
    </li>
  );
}
