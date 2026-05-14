"use client";

import * as React from "react";
import { useCallback, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Clock,
  Zap,
  CheckCircle2,
  Circle,
  Loader2,
  Copy,
  Download,
} from "lucide-react";
import { useInstallationRuns } from "@/hooks/use-installation-runs";
import { PremiumCard } from "@/components/ui/premium-card";
import { RunStatusBadge } from "@/components/product/run-status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { AgentRun } from "@/types";

type SearchParamsRecord = Record<string, string | string[] | undefined>;

function getParam(sp: SearchParamsRecord | undefined, key: string): string | null {
  if (!sp || !(key in sp)) return null;
  const v = sp[key];
  return Array.isArray(v) ? v[0] ?? null : (v ?? null);
}

function copyToClipboard(text: string) {
  return navigator.clipboard.writeText(text);
}

function downloadAsFile(filename: string, content: string) {
  const blob = new Blob([content], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const STEPS = [
  { key: "queued", label: "Queued", icon: Circle },
  { key: "running", label: "Running", icon: Loader2 },
  { key: "completed", label: "Completed", icon: CheckCircle2 },
];

export default function RunExecutionPage({
  params,
  searchParams,
}: {
  params: Promise<{ runId?: string }>;
  searchParams?: Promise<SearchParamsRecord>;
}) {
  const resolvedParams = React.use(params);
  const resolvedSearchParams = React.use(searchParams ?? Promise.resolve({}));
  const runId = Number(resolvedParams.runId);
  const installationId = Number(getParam(resolvedSearchParams, "installation_id") || 0);

  const { runs, loading, error } = useInstallationRuns(
    installationId > 0 ? installationId : null,
    100
  );
  const run = runs.find((r) => r.run_id === runId) ?? null;

  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(() => {
    if (!run?.output) return;
    const text =
      typeof run.output === "string"
        ? run.output
        : JSON.stringify(run.output, null, 2);
    copyToClipboard(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [run?.output]);

  const handleDownload = useCallback(() => {
    if (!run?.output) return;
    const text =
      typeof run.output === "string"
        ? run.output
        : JSON.stringify(run.output, null, 2);
    downloadAsFile(
      `run-${run.run_id}-${run.task_id}-output.json`,
      text
    );
  }, [run]);

  if (loading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-9 w-48 bg-elevated" />
        <Skeleton className="h-40 rounded-xl bg-card" />
        <Skeleton className="h-64 rounded-xl bg-card" />
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="space-y-6">
        <Link
          href="/runs"
          className="inline-flex items-center gap-2 text-body text-foreground-secondary hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Run history
        </Link>
        <p className="text-body text-muted">Run not found.</p>
      </div>
    );
  }

  const statusLower = run.status?.toLowerCase() ?? "";
  const stepIndex =
    statusLower === "completed" || statusLower === "failed"
      ? 2
      : statusLower === "running"
        ? 1
        : 0;
  const output =
    run.output == null
      ? ""
      : typeof run.output === "string"
        ? run.output
        : JSON.stringify(run.output, null, 2);

  return (
    <div className="space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Link
          href="/runs"
          className="inline-flex items-center gap-2 text-body text-foreground-secondary hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Run history
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-page-title text-foreground tracking-tight">
              Run execution
            </h1>
            <p className="mt-1 text-body text-foreground-secondary">
              Run ID {run.run_id} · Task {run.task_id}
            </p>
          </div>
          <RunStatusBadge status={run.status} />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-6 text-body text-muted">
          <span className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            {run.created_at}
          </span>
          {run.execution_time_ms > 0 && (
            <span className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              {run.execution_time_ms}ms
            </span>
          )}
        </div>
      </motion.div>

      {/* Execution timeline */}
      <PremiumCard>
        <h2 className="text-section-title text-foreground mb-6">
          Execution timeline
        </h2>
        <div className="flex items-center gap-4">
          {STEPS.map((step, i) => {
            const isActive = i <= stepIndex;
            const isCurrent = i === stepIndex;
            const Icon = step.icon;
            return (
              <div
                key={step.key}
                className="flex flex-1 items-center gap-2"
              >
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
                    isActive
                      ? "border-primary bg-primary-soft text-primary"
                      : "border-border text-muted"
                  }`}
                >
                  {step.key === "running" && isCurrent ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Icon className="h-5 w-5" />
                  )}
                </div>
                <span
                  className={`text-label ${
                    isActive ? "text-foreground" : "text-muted"
                  }`}
                >
                  {step.label}
                </span>
                {i < STEPS.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 rounded ${
                      i < stepIndex ? "bg-primary" : "bg-border"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </PremiumCard>

      {/* Logs / output — developer console feel */}
      <PremiumCard>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-section-title text-foreground">
            Output
          </h2>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleCopy}
              className="gap-2"
            >
              <Copy className="h-4 w-4" />
              {copied ? "Copied" : "Copy"}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleDownload}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Download
            </Button>
          </div>
        </div>
        {output ? (
          <pre className="rounded-lg border border-border bg-background p-4 text-body text-foreground-secondary overflow-x-auto whitespace-pre-wrap font-mono">
            {output}
          </pre>
        ) : (
          <p className="text-body text-muted py-8">No output recorded.</p>
        )}
      </PremiumCard>
    </div>
  );
}
