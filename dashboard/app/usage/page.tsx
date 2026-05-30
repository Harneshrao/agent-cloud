"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { BarChart3, CreditCard, Gauge } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useDashboard } from "@/hooks/use-dashboard";
import { fetchBillingSummary } from "@/lib/api";
import { ProjectGate } from "@/components/product/project-gate";
import { friendlyApiError } from "@/lib/project-messages";
import { ApiConnectionBanner } from "@/components/api-connection-banner";
import { MetricCard } from "@/components/ui/metric-card";
import { PremiumCard } from "@/components/ui/premium-card";
import { Skeleton } from "@/components/ui/skeleton";

export default function UsagePage() {
  const { data, loading, refetch } = useDashboard();
  const [billing, setBilling] = useState<Awaited<
    ReturnType<typeof fetchBillingSummary>
  > | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchBillingSummary();
        if (!cancelled) setBilling(res);
      } catch {
        if (!cancelled) setBilling(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const runsPerAgent = data?.runs_per_agent ?? [];

  if (loading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-9 w-64 bg-elevated" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 rounded-xl bg-card" />
          ))}
        </div>
        <Skeleton className="h-80 rounded-xl bg-card" />
      </div>
    );
  }
  const chartData = runsPerAgent.map((r) => ({
    name: r.agent_name.length > 10 ? r.agent_name.slice(0, 10) + "â€¦" : r.agent_name,
    runs: r.runs,
    cost: Number((r.total_agent_cost ?? 0).toFixed(2)),
  }));

  return (
    <ProjectGate>
    <div className="space-y-8">
      <ApiConnectionBanner onReady={refetch} />

      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-page-title text-foreground tracking-tight">
          Usage & Billing
        </h1>
        <p className="mt-2 max-w-2xl text-body text-foreground-secondary">
          Track executions, retries, and runtime activity for this project. Charts fill in as you run tasks.
        </p>
      </motion.div>

      {billing?.warnings && billing.warnings.length > 0 ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm text-amber-200">
          {billing.warnings.map((w) => (
            <p key={w.code}>
              {w.message}{" "}
              <Link href="/limits" className="underline text-amber-100">
                View limits
              </Link>
            </p>
          ))}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Runs this month"
          value={
            billing?.usage.runs_enqueued ??
            data?.monthly_usage?.runs_this_month ??
            0
          }
        />
        <MetricCard
          label="Execution time (min)"
          value={Math.round(
            (billing?.usage.execution_time_ms ?? 0) / 60_000
          )}
        />
        <MetricCard
          label="Retries / DLQ"
          value={`${billing?.usage.retries ?? 0} / ${billing?.usage.dlq_entries ?? 0}`}
        />
        <MetricCard
          label="Agent cost (est.)"
          value={Number(data?.total_agent_cost ?? 0)}
          format={(n) => `$${n.toFixed(2)}`}
        />
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <PremiumCard>
            <h2 className="text-section-title text-foreground flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-muted" />
              Cost per agent
            </h2>
            <p className="mt-0.5 text-body text-foreground-secondary">
              Monthly spending by agent
            </p>
            {chartData.length === 0 ? (
              <p className="mt-8 py-12 text-center text-body text-muted">
                No usage yet.
              </p>
            ) : (
              <div className="mt-6 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartData}
                    margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--border)"
                    />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11, fill: "var(--muted)" }}
                      axisLine={{ stroke: "var(--border)" }}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "var(--muted)" }}
                      axisLine={{ stroke: "var(--border)" }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--card)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                      }}
                      labelStyle={{ color: "var(--foreground)" }}
                    />
                    <Bar
                      dataKey="cost"
                      fill="var(--primary)"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </PremiumCard>

          <PremiumCard>
            <h2 className="text-section-title text-foreground">
              Cost per day
            </h2>
            <p className="mt-0.5 text-body text-foreground-secondary">
              Daily breakdown (today: ${(data?.cost_today ?? 0).toFixed(2)})
            </p>
            <div className="mt-6 space-y-4">
              {runsPerAgent.length === 0 ? (
                <p className="text-body text-muted">No usage yet.</p>
              ) : (
                runsPerAgent.slice(0, 8).map((r) => (
                  <div
                    key={r.agent_name}
                    className="flex items-center justify-between rounded-lg border border-border bg-elevated/30 px-4 py-3"
                  >
                    <span className="text-body text-foreground truncate">
                      {r.agent_name}
                    </span>
                    <span className="text-body text-foreground-secondary shrink-0">
                      ${(r.total_agent_cost ?? 0).toFixed(2)} total
                      {r.cost_per_run != null &&
                        ` Â· $${r.cost_per_run.toFixed(2)}/run`}
                    </span>
                  </div>
                ))
              )}
            </div>
          </PremiumCard>
        </div>

        <div className="space-y-6">
          <PremiumCard>
            <h2 className="text-section-title text-foreground flex items-center gap-2">
              <Gauge className="h-5 w-5 text-muted" />
              Plan & quotas
            </h2>
            <p className="mt-0.5 text-body text-foreground-secondary">
              {billing?.plan.name ?? "Free"} plan · enforcement before scale
            </p>
            <ul className="mt-4 space-y-2 text-body text-foreground-secondary">
              <li>
                Deployments: {billing?.usage.deployments ?? 0} /{" "}
                {billing?.limits.max_deployments ?? "—"}
              </li>
              <li>
                Storage: {billing?.usage.artifact_storage_mb ?? 0} MB /{" "}
                {billing?.limits.max_artifact_storage_mb ?? "—"} MB
              </li>
              <li>
                Concurrent: {billing?.usage.concurrent_running ?? 0} /{" "}
                {billing?.limits.max_concurrent_running ?? "—"}
              </li>
            </ul>
            <Link
              href="/limits"
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-elevated px-4 py-2.5 text-sm font-medium text-foreground hover:bg-elevated/80"
            >
              <CreditCard className="h-4 w-4" />
              View limits & warnings
            </Link>
          </PremiumCard>
        </div>
      </div>
    </div>
    </ProjectGate>
  );
}
