"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { trackProductEvent } from "@/lib/analytics";
import { fetchObservabilityDlq } from "@/lib/api";
import { friendlyApiError } from "@/lib/project-messages";
import type { DlqItem } from "@/types";
import { EmptyState } from "@/components/product/empty-state";
import { ProjectGate } from "@/components/product/project-gate";
import { GlassCard } from "@/components/product/glass-card";
import { Skeleton } from "@/components/ui/skeleton";

export default function DlqPage() {
  const [items, setItems] = useState<DlqItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    trackProductEvent("dlq_viewed");
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchObservabilityDlq();
        if (!cancelled) setItems(res.dead_letters ?? []);
      } catch (e) {
        if (!cancelled) {
          setError(friendlyApiError(e instanceof Error ? e.message : "Failed to load failed tasks"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <ProjectGate>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Failed tasks</h1>
          <p className="mt-1 max-w-2xl text-sm text-neutral-400">
            Tasks that could not complete successfully appear here for recovery and retry. This is
            normal while testing — inspect the trace, fix your agent, and redeploy.
          </p>
        </div>

        {error ? (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        ) : null}

        {loading ? (
          <Skeleton className="h-64 rounded-2xl" />
        ) : (
          <GlassCard className="overflow-hidden">
            {items.length === 0 ? (
              <EmptyState
                icon={AlertTriangle}
                title="No failed tasks — that's good"
                description="When a task exhausts retries, it lands here with the error message."
                why="Try the sample_fail agent on Deployments to see retries and recovery in action."
                actionLabel="Deploy sample_fail"
                actionHref="/deployments"
                secondaryLabel="View runs"
                secondaryHref="/runs"
              />
            ) : (
              <ul className="divide-y divide-white/5">
                {items.map((item) => (
                  <li key={item.task_id} className="px-6 py-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium text-foreground">
                          {item.agent_name || "Unknown agent"}
                        </p>
                        <p className="text-sm text-neutral-500">Task failed after retries</p>
                      </div>
                      <Link
                        href={`/tasks/${item.task_id}`}
                        className="text-sm font-medium text-primary hover:underline"
                      >
                        View trace & logs
                      </Link>
                    </div>
                    <p className="mt-2 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
                      {item.error || "No error message recorded"}
                    </p>
                    <p className="mt-3 flex flex-wrap gap-3 text-sm">
                      <Link
                        href={`/tasks/${item.task_id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        View trace
                      </Link>
                      <Link href="/deployments" className="text-neutral-500 hover:text-primary">
                        Redeploy echo sample
                      </Link>
                    </p>
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
