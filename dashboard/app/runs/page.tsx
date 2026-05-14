"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { fetchDashboard } from "@/lib/api";
import type { DashboardData } from "@/types";
import { GlassCard } from "@/components/product/glass-card";
import { RunStatusBadge } from "@/components/product/run-status-badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function RunHistoryPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetchDashboard();
        if (!cancelled) setData(res);
      } catch {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
  }, []);

  const runs = data?.recent_runs ?? [];

  return (
    <div className="space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Run history
        </h1>
        <p className="mt-1 text-neutral-400">
          All recent runs. Click a run to view its output.
        </p>
      </motion.div>

      {loading ? (
        <Skeleton className="h-96 rounded-2xl" />
      ) : (
        <GlassCard className="overflow-hidden">
          {runs.length === 0 ? (
            <div className="p-12 text-center text-neutral-500">
              No runs yet. Run an agent from Home to see results here.
            </div>
          ) : (
            <ul className="divide-y divide-white/5">
              {runs.map((run) => (
                <li key={`${run.run_id}-${run.task_id}`}>
                  <Link
                    href={`/runs/${run.run_id}?installation_id=${run.installation_id}`}
                    className="flex items-center justify-between px-6 py-4 transition-colors hover:bg-white/[0.03]"
                  >
                    <div>
                      <p className="font-medium text-foreground">{run.agent_name}</p>
                      <p className="text-sm text-neutral-500 mt-0.5">
                        {run.created_at}
                        {run.execution_time_ms > 0 && ` · ${run.execution_time_ms}ms`}
                      </p>
                    </div>
                    <RunStatusBadge status={run.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>
      )}
    </div>
  );
}
