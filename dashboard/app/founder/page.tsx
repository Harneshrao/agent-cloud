"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchPmfSummary } from "@/lib/api";
import type { PmfSummary } from "@/lib/analytics";
import { PlatformAlert } from "@/components/product/platform-alert";
import { PageLoader } from "@/components/product/page-state";
import { GlassCard } from "@/components/product/glass-card";
import { StatCard } from "@/components/product/stat-card";
import { Button } from "@/components/ui/button";

const EVENT_LABELS: Record<string, string> = {
  signup_completed: "Signup",
  project_created: "Project",
  artifact_upload_succeeded: "Upload OK",
  deployment_created: "Deployed",
  first_task_completed: "First run ✓",
  trace_viewed: "Trace viewed",
  api_key_created: "API key",
};

export default function FounderPmfPage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<PmfSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPmfSummary(days);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load PMF metrics");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  const chartData =
    data?.funnel.steps.map((s) => ({
      name: EVENT_LABELS[s.event] ?? s.event,
      count: s.count,
    })) ?? [];

  const deployment = data?.deployment as Record<string, number | null> | undefined;
  const trust = data?.trust as Record<string, number | null> | undefined;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-primary">
            Founder · internal only
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            PMF & activation
          </h1>
          <p className="mt-1 max-w-2xl text-neutral-400">
            Where developers succeed, fail, and abandon — derived from real product events and
            usage ledger.
          </p>
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map((d) => (
            <Button
              key={d}
              type="button"
              variant={days === d ? "default" : "outline"}
              size="sm"
              onClick={() => setDays(d)}
            >
              {d}d
            </Button>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={load}>
            Refresh
          </Button>
        </div>
      </div>

      {error ? <PlatformAlert error={error} onRetry={load} /> : null}
      {loading ? <PageLoader loaderClassName="h-48 rounded-2xl" /> : null}

      {data && !loading ? (
        <>
          {(data.ops_alerts ?? []).length > 0 ? (
            <GlassCard className="border-amber-500/30 p-6">
              <h2 className="text-lg font-semibold text-foreground">Alpha ops alerts</h2>
              <p className="mt-1 text-sm text-neutral-400">
                Triage before replying in Slack — ordered by severity.
              </p>
              <ul className="mt-4 space-y-2">
                {data.ops_alerts!.map((a) => (
                  <li
                    key={a.code}
                    className={`rounded-lg px-4 py-3 text-sm ${
                      a.severity === "critical" || a.severity === "high"
                        ? "bg-red-500/10 text-red-200"
                        : "bg-amber-500/10 text-amber-100"
                    }`}
                  >
                    <span className="font-medium uppercase text-xs opacity-70">
                      {a.severity}
                    </span>
                    <p className="mt-0.5">{a.message}</p>
                  </li>
                ))}
              </ul>
            </GlassCard>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="PMF health"
              value={`${data.pmf_health.score}`}
              sub={`${data.pmf_health.label} · composite score`}
            />
            <StatCard
              label="Activation rate"
              value={`${data.funnel.activation_rate_pct}%`}
              sub={`${data.funnel.activated_users} activated / ${data.funnel.signup_users} signups`}
            />
            <StatCard
              label="Upload success"
              value={
                deployment?.upload_success_rate_pct != null
                  ? `${deployment.upload_success_rate_pct}%`
                  : "—"
              }
              sub={`${deployment?.artifact_uploads ?? 0} uploads`}
            />
            <StatCard
              label="Task success"
              value={
                trust?.task_success_rate_pct != null ? `${trust.task_success_rate_pct}%` : "—"
              }
              sub={`${trust?.tasks_completed ?? 0} completed`}
            />
          </div>

          <GlassCard className="p-6">
            <h2 className="text-lg font-semibold text-foreground">Activation funnel</h2>
            <p className="mt-1 text-sm text-neutral-400">
              Drop-off between steps shows where onboarding breaks.
              {data.funnel.median_time_to_activation_seconds != null
                ? ` Median time to first run: ${Math.round(
                    data.funnel.median_time_to_activation_seconds / 60
                  )} min.`
                : ""}
            </p>
            <div className="mt-6 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
                  <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    stroke="#94a3b8"
                    fontSize={12}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#1e293b",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <ul className="mt-4 divide-y divide-white/5 text-sm">
              {data.funnel.steps.map((step) => (
                <li
                  key={step.event}
                  className="flex justify-between py-2 text-neutral-400"
                >
                  <span>{EVENT_LABELS[step.event] ?? step.event}</span>
                  <span>
                    {step.count} users
                    {step.drop_off_pct_from_previous != null
                      ? ` · −${step.drop_off_pct_from_previous}%`
                      : ""}
                  </span>
                </li>
              ))}
            </ul>
          </GlassCard>

          {(data.activation_gaps ?? null) ? (
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-foreground">Activation gaps</h2>
              <p className="mt-1 text-sm text-neutral-400">
                Where users stall between deploy → run → trace → key → repeat.
              </p>
              <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
                <MetricRow
                  label="Deploy, no run"
                  value={data.activation_gaps!.deploy_without_run_users}
                />
                <MetricRow
                  label="Run, no trace"
                  value={data.activation_gaps!.run_without_trace_users}
                />
                <MetricRow
                  label="Trace, no key"
                  value={data.activation_gaps!.trace_without_key_users}
                />
                <MetricRow
                  label="Second-run signals"
                  value={data.activation_gaps!.second_task_starts}
                />
                <MetricRow
                  label="Run again clicks"
                  value={data.activation_gaps!.run_again_clicks}
                />
                <MetricRow
                  label="Repeat rate"
                  value={
                    data.activation_gaps!.repeat_rate_pct != null
                      ? `${data.activation_gaps!.repeat_rate_pct}%`
                      : "—"
                  }
                />
                <MetricRow
                  label="Deploy-without-run views"
                  value={data.activation_gaps!.deploy_without_run_views}
                />
                <MetricRow label="Run CTA clicks" value={data.activation_gaps!.run_cta_clicks} />
                <MetricRow label="Page views" value={data.activation_gaps!.page_views} />
              </dl>
            </GlassCard>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-2">
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-foreground">Deployment health</h2>
              <dl className="mt-4 grid gap-2 text-sm">
                <MetricRow label="Deployments created" value={deployment?.deployments_created} />
                <MetricRow label="Deploy failures" value={deployment?.deployment_failures} />
                <MetricRow label="Upload failures" value={deployment?.artifact_upload_failures} />
                <MetricRow label="Rollbacks" value={deployment?.rollbacks} />
                <MetricRow label="Sample deploy clicks" value={deployment?.sample_deploy_requests} />
              </dl>
            </GlassCard>
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-foreground">Trust & reliability</h2>
              <dl className="mt-4 grid gap-2 text-sm">
                <MetricRow label="Tasks completed" value={trust?.tasks_completed} />
                <MetricRow label="Tasks failed" value={trust?.tasks_failed} />
                <MetricRow label="Retries" value={trust?.retries} />
                <MetricRow label="DLQ entries" value={trust?.dlq_entries} />
                <MetricRow label="Trace views" value={trust?.trace_views} />
                <MetricRow label="Retry clicks (UI)" value={trust?.retry_clicks} />
              </dl>
            </GlassCard>
          </div>

          {data.recent_feedback.length > 0 ? (
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-foreground">Recent feedback</h2>
              <ul className="mt-4 space-y-3 text-sm">
                {data.recent_feedback.map((f) => (
                  <li
                    key={f.event_id}
                    className="rounded-lg border border-white/5 px-4 py-3 text-neutral-300"
                  >
                    <span className="text-primary">
                      ★ {(f.properties as { rating?: number }).rating ?? "?"}
                    </span>
                    <span className="ml-2 text-neutral-500">{f.created_at}</span>
                    <p className="mt-1">
                      {(f.properties as { comment?: string }).comment ||
                        (f.properties as { context?: string }).context ||
                        "—"}
                    </p>
                  </li>
                ))}
              </ul>
            </GlassCard>
          ) : null}

          {(data.user_research_cohort ?? []).length > 0 ? (
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-foreground">User research cohort</h2>
              <p className="mt-1 text-sm text-neutral-400">
                Recent users × funnel steps — First 5 users program. See docs/FIRST_5_USERS.md.
              </p>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="text-neutral-500">
                      <th className="pb-2 pr-4 font-medium">User</th>
                      <th className="pb-2 pr-4 font-medium">TTA</th>
                      <th className="pb-2 pr-4 font-medium">Deploy</th>
                      <th className="pb-2 pr-4 font-medium">Run</th>
                      <th className="pb-2 pr-4 font-medium">Trace</th>
                      <th className="pb-2 pr-4 font-medium">Key</th>
                      <th className="pb-2 pr-4 font-medium">Again?</th>
                      <th className="pb-2 font-medium">Help?</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {data.user_research_cohort!.map((u) => (
                      <tr key={u.user_id} className="text-neutral-300">
                        <td className="py-2 pr-4 font-mono text-xs">{u.user_id.slice(0, 8)}…</td>
                        <td className="py-2 pr-4">
                          {u.time_to_activation_seconds != null
                            ? `${Math.round(u.time_to_activation_seconds / 60)}m`
                            : "—"}
                        </td>
                        <td className="py-2 pr-4">{step(u.steps, "deployment_created")}</td>
                        <td className="py-2 pr-4">{step(u.steps, "first_task_completed")}</td>
                        <td className="py-2 pr-4">{step(u.steps, "trace_viewed")}</td>
                        <td className="py-2 pr-4">{step(u.steps, "api_key_created")}</td>
                        <td className="py-2 pr-4">{u.would_use_again ?? "—"}</td>
                        <td className="py-2">
                          {u.needed_help === true ? "yes" : u.needed_help === false ? "no" : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value?: number | null }) {
  return (
    <div className="flex justify-between">
      <dt className="text-neutral-400">{label}</dt>
      <dd className="font-medium text-foreground">{value ?? "—"}</dd>
    </div>
  );
}

function step(steps: Record<string, boolean>, key: string) {
  return steps[key] ? "✓" : "—";
}
