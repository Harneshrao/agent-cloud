"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlayCircle } from "lucide-react";
import { fetchObservabilityTasks } from "@/lib/api";
import { trackProductEvent } from "@/lib/analytics";
import { markOnboardingStep } from "@/lib/onboarding";
import { ACTIVATION_COPY } from "@/lib/trust-copy";
import { friendlyApiError } from "@/lib/project-messages";
import type { TaskListItem } from "@/types";
import { EmptyState } from "@/components/product/empty-state";
import { PlatformAlert } from "@/components/product/platform-alert";
import { PageLoader } from "@/components/product/page-state";
import { ProjectGate } from "@/components/product/project-gate";
import { GlassCard } from "@/components/product/glass-card";

function statusColor(status: string) {
  if (status === "completed") return "text-green-400";
  if (status === "failed" || status === "dead") return "text-red-400";
  if (status === "running") return "text-primary";
  return "text-neutral-400";
}

export default function RunHistoryPage() {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const taskRes = await fetchObservabilityTasks(50);
        if (!cancelled) {
          setTasks(taskRes.tasks ?? []);
        }
      } catch (e) {
        if (!cancelled) {
          setError(friendlyApiError(e instanceof Error ? e.message : "Failed to load runs"));
          setTasks([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <ProjectGate>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Runs & traces</h1>
          <p className="mt-1 text-neutral-400">
            {ACTIVATION_COPY.runsNavHint} Open any row for status, result, and logs.
          </p>
        </div>

        {error ? (
          <PlatformAlert
            error={error}
            onRetry={() => {
              setLoading(true);
              setError(null);
              fetchObservabilityTasks(50)
                .then((taskRes) => setTasks(taskRes.tasks ?? []))
                .catch((e) =>
                  setError(
                    friendlyApiError(e instanceof Error ? e.message : "Failed to load runs")
                  )
                )
                .finally(() => setLoading(false));
            }}
          />
        ) : null}

        {loading ? (
          <PageLoader loaderClassName="h-96 rounded-2xl" />
        ) : (
          <GlassCard className="overflow-hidden">
            {tasks.length === 0 ? (
              <EmptyState
                icon={PlayCircle}
                title="No runs yet"
                description="Deploy an agent, then click Run task on the Deployments page."
                why="A run is one execution of your agent — you'll see status, duration, and logs."
                actionLabel="Go to Deployments"
                actionHref="/deployments"
              />
            ) : (
              <ul className="divide-y divide-white/5">
                {tasks.map((t) => (
                  <li key={t.task_id}>
                    <Link
                      href={`/tasks/${t.task_id}`}
                      onClick={() => {
                        markOnboardingStep("viewed_logs");
                        trackProductEvent("trace_viewed", { task_id: t.task_id });
                      }}
                      className="flex items-center justify-between px-6 py-4 transition-colors hover:bg-white/[0.03]"
                    >
                      <div>
                        <p className="font-medium text-foreground">
                          {t.agent_name || "Agent task"}
                        </p>
                        <p className="mt-0.5 text-sm text-neutral-500">
                          {t.created_at}
                          {t.execution_time_ms != null && t.execution_time_ms > 0
                            ? ` · ${t.execution_time_ms}ms`
                            : ""}
                        </p>
                      </div>
                      <span className={`text-sm font-medium capitalize ${statusColor(t.status)}`}>
                        {t.status}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </GlassCard>
        )}
      </div>
    </ProjectGate>
  );
}
