"use client";

import { useCallback, useEffect, useState } from "react";
import { Server } from "lucide-react";
import { fetchObservabilityHealth } from "@/lib/api";
import { EmptyState } from "@/components/product/empty-state";
import { PlatformAlert } from "@/components/product/platform-alert";
import { PageLoader } from "@/components/product/page-state";
import { ProjectGate } from "@/components/product/project-gate";
import { GlassCard } from "@/components/product/glass-card";

export default function WorkersPage() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      const h = await fetchObservabilityHealth();
      setHealth(h);
      setError(null);
    } catch (e) {
      setError(e);
    }
  }, []);

  useEffect(() => {
    load().finally(() => setLoading(false));
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [load]);

  const platform = (health?.platform ?? {}) as Record<string, unknown>;
  const queue = (health?.queue ?? {}) as Record<string, unknown>;
  const workersActive = Number(platform.workers_active ?? 0);

  return (
    <ProjectGate>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Workers</h1>
          <p className="mt-1 max-w-2xl text-sm text-neutral-400">
            Workers automatically process your tasks as executions arrive. You rarely need to
            visit this page — it confirms your queue is being drained after you run an agent.
          </p>
        </div>

        {error ? <PlatformAlert error={error} onRetry={load} /> : null}

        {loading ? (
          <PageLoader />
        ) : workersActive === 0 && !error ? (
          <GlassCard>
            <EmptyState
              icon={Server}
              title="No workers connected yet"
              description="When workers are online, tasks from Deployments move from queued to running automatically."
              why="Run a task on Deployments first — this page will show activity within seconds."
              actionLabel="Run your first task"
              actionHref="/deployments"
            />
          </GlassCard>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            <GlassCard className="p-4">
              <p className="text-xs text-neutral-500">Processing tasks</p>
              <p className="mt-1 text-2xl font-semibold text-foreground">{workersActive}</p>
              <p className="mt-1 text-xs text-emerald-400/80">Workers online</p>
            </GlassCard>
            <GlassCard className="p-4">
              <p className="text-xs text-neutral-500">Waiting in queue</p>
              <p className="mt-1 text-2xl font-semibold text-foreground">
                {String(queue.ready_depth ?? queue.depth ?? "0")}
              </p>
              <p className="mt-1 text-xs text-neutral-500">Tasks not yet picked up</p>
            </GlassCard>
            <GlassCard className="p-4">
              <p className="text-xs text-neutral-500">Platform health</p>
              <p className="mt-1 text-sm font-medium text-emerald-400">Operational</p>
              <p className="mt-1 text-xs text-neutral-500">Execution pipeline active</p>
            </GlassCard>
          </div>
        )}
      </div>
    </ProjectGate>
  );
}
