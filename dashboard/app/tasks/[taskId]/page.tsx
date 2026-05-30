"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { PlayCircle } from "lucide-react";
import { fetchTaskTrace, runDeployment } from "@/lib/api";
import { trackProductEvent } from "@/lib/analytics";
import { markOnboardingStep } from "@/lib/onboarding";
import { ProjectGate } from "@/components/product/project-gate";
import type { TaskTrace } from "@/types";
import { GlassCard } from "@/components/product/glass-card";
import { SuccessBanner } from "@/components/product/success-banner";
import { PlatformAlert } from "@/components/product/platform-alert";
import { PageLoader } from "@/components/product/page-state";
import { ExecutionStarting } from "@/components/product/execution-starting";
import { TracePostSuccessPanel } from "@/components/product/trace-post-success-panel";
import { Button } from "@/components/ui/button";
import { SUCCESS_MESSAGES, ACTIVATION_COPY } from "@/lib/trust-copy";
import { trackRunAgainClicked } from "@/lib/analytics";

function statusLabel(status: string): string {
  const s = status.toLowerCase();
  if (s === "completed") return "Completed successfully";
  if (s === "running") return "Running now";
  if (s === "queued" || s === "pending") return "Queued — waiting for a worker";
  if (s === "failed" || s === "dead") return "Did not succeed";
  return status;
}

function formatOutput(output: unknown): string {
  if (output == null) return "";
  if (typeof output === "string") return output;
  try {
    return JSON.stringify(output, null, 2);
  } catch {
    return String(output);
  }
}

export default function TaskTracePage() {
  const params = useParams();
  const router = useRouter();
  const taskId = String(params.taskId ?? "");
  const [trace, setTrace] = useState<TaskTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [runningAgain, setRunningAgain] = useState(false);

  const load = useCallback(async () => {
    if (!taskId) return;
    setError(null);
    try {
      const res = await fetchTaskTrace(taskId);
      setTrace(res);
      markOnboardingStep("viewed_logs");
      trackProductEvent("trace_viewed", { task_id: taskId });
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load]);

  const task = trace?.task as Record<string, unknown> | undefined;
  const status = String(task?.status ?? "");
  const deploymentId = task?.deployment_id
    ? String(task.deployment_id)
    : (task?.input as Record<string, unknown> | undefined)?.deployment_id
      ? String((task?.input as Record<string, unknown>).deployment_id)
      : "";
  const failed = status === "failed" || status === "dead";
  const completed = status === "completed";
  const inProgress = status === "running" || status === "queued" || status === "pending";

  useEffect(() => {
    if (!inProgress || !taskId) return;
    const id = setInterval(() => {
      void load();
    }, 2500);
    return () => clearInterval(id);
  }, [inProgress, taskId, load]);

  async function onRunAgain() {
    if (!deploymentId) {
      router.push("/deployments");
      return;
    }
    setRunningAgain(true);
    setError(null);
    try {
      const res = await runDeployment(deploymentId, { message: "hello from Agent Cloud" });
      markOnboardingStep("ran");
      if (res.task_id) {
        router.push(`/tasks/${res.task_id}`);
      }
    } catch (e) {
      setError(e);
      setRunningAgain(false);
    }
  }

  const output = task?.output;
  const errorFromEvents = (trace?.events ?? []).find((e) => e.payload?.error)?.payload?.error;

  return (
    <ProjectGate>
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link href="/runs" className="text-sm text-neutral-500 hover:text-primary">
              ← Runs & traces
            </Link>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
              Execution trace
            </h1>
            <p className="mt-1 text-sm text-neutral-500">{ACTIVATION_COPY.runsNavHint}</p>
          </div>
          {deploymentId && !inProgress && !completed ? (
            <Button
              type="button"
              disabled={runningAgain}
              onClick={() => {
                trackRunAgainClicked(taskId, deploymentId);
                void onRunAgain();
              }}
            >
              <PlayCircle className="mr-2 h-4 w-4" />
              {runningAgain ? "Starting…" : "Run again"}
            </Button>
          ) : null}
        </div>

        {completed ? <SuccessBanner message={SUCCESS_MESSAGES.logsStreaming} /> : null}

        {failed ? (
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-4 text-sm">
            <p className="font-medium text-amber-50">This run did not succeed</p>
            <p className="mt-1 text-amber-100/85">
              Read the error below, then fix your agent on Deployments and redeploy — or switch
              back to the echo sample and use <strong className="font-medium">Run again</strong>.
            </p>
            {deploymentId ? (
              <Button
                type="button"
                size="sm"
                className="mt-3"
                disabled={runningAgain}
                onClick={() => {
                  trackRunAgainClicked(taskId, deploymentId);
                  void onRunAgain();
                }}
              >
                Run again
              </Button>
            ) : (
              <Link href="/deployments" className="mt-2 inline-block text-primary hover:underline">
                Go to Deployments
              </Link>
            )}
          </div>
        ) : null}

        {runningAgain ? <ExecutionStarting /> : null}
        {error ? <PlatformAlert error={error} onRetry={load} /> : null}

        {loading && !trace ? (
          <PageLoader loaderClassName="h-96 rounded-2xl" />
        ) : trace ? (
          <>
            <GlassCard className="p-6">
              <dl className="grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                    Status
                  </dt>
                  <dd className="mt-1 text-lg font-medium capitalize text-foreground">
                    {statusLabel(status)}
                  </dd>
                </div>
                {completed && output != null ? (
                  <div className="sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                      Result
                    </dt>
                    <dd className="mt-2 max-h-48 overflow-auto rounded-lg bg-black/30 p-3 font-mono text-xs text-emerald-100/90">
                      {formatOutput(output)}
                    </dd>
                  </div>
                ) : null}
                {failed && errorFromEvents ? (
                  <div className="sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                      Error
                    </dt>
                    <dd className="mt-2 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
                      {String(errorFromEvents)}
                    </dd>
                  </div>
                ) : null}
              </dl>
            </GlassCard>

            <GlassCard className="overflow-hidden">
              <div className="border-b border-white/5 px-6 py-3 text-sm font-medium text-neutral-300">
                Logs
              </div>
              <ul className="max-h-[28rem] divide-y divide-white/5 overflow-y-auto font-mono text-xs">
                {(trace.logs ?? []).length === 0 ? (
                  <li className="px-6 py-4 text-neutral-500">
                    {inProgress
                      ? "Waiting for logs — your agent is starting up…"
                      : "No log lines recorded for this run."}
                  </li>
                ) : (
                  (trace.logs ?? []).map((log, i) => (
                    <li key={i} className="px-6 py-2 text-neutral-400">
                      <span className="text-neutral-500">{String(log.created_at ?? "")}</span>{" "}
                      <span className="text-foreground">
                        {String(log.message ?? log.event_type ?? "")}
                      </span>
                    </li>
                  ))
                )}
              </ul>
            </GlassCard>

            {(trace.events ?? []).length > 0 ? (
              <details className="group">
                <summary className="cursor-pointer text-sm text-neutral-500 hover:text-neutral-400">
                  Technical timeline ({trace.events.length} events)
                </summary>
                <GlassCard className="mt-2 overflow-hidden">
                  <ul className="divide-y divide-white/5 font-mono text-xs">
                    {(trace.events ?? []).map((ev) => (
                      <li key={ev.event_id} className="px-6 py-3">
                        <span className="text-primary">{ev.event_type}</span>
                        <span className="ml-3 text-neutral-500">{ev.created_at}</span>
                      </li>
                    ))}
                  </ul>
                </GlassCard>
              </details>
            ) : null}

            {completed && deploymentId ? (
              <TracePostSuccessPanel
                taskId={taskId}
                deploymentId={deploymentId}
                running={runningAgain}
                onRunAgain={() => void onRunAgain()}
              />
            ) : null}
          </>
        ) : null}
      </div>
    </ProjectGate>
  );
}
