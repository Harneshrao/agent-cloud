"use client";

import { useApi } from "@/hooks/useApi";
import type { DashboardData } from "@/types";
import { MetricCard } from "@/components/ui/metric-card";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Bot } from "lucide-react";

export default function Dashboard() {
  const { data, loading, error } = useApi<DashboardData>("/dashboard");

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <div className="page-title">Dashboard</div>
          <div className="page-subtitle">Overview of your agents and activity.</div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[92px] rounded-xl bg-card" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Skeleton className="h-[340px] rounded-xl bg-card lg:col-span-2" />
          <Skeleton className="h-[340px] rounded-xl bg-card" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 shadow-soft">
        <div className="page-title">Dashboard</div>
        <div className="page-subtitle">We couldn’t load your data right now.</div>
        <div className="mt-4 text-sm text-error">{error}</div>
      </div>
    );
  }
  if (!data) return null;

  const runsToday = data.runs_today ?? 0;
  const costToday = Number(data.cost_today ?? 0);
  const monthlyRuns = data.monthly_usage?.runs_this_month ?? 0;
  const totalSpend = Number(data.total_agent_cost ?? 0);

  const installations = data.installations ?? [];
  const recentRuns = data.recent_runs ?? [];

  const lastRunByInstallation = new Map<number, DashboardData["recent_runs"][number]>();
  for (const r of recentRuns) {
    const existing = lastRunByInstallation.get(r.installation_id);
    if (!existing || (r.created_at || "") > (existing.created_at || "")) {
      lastRunByInstallation.set(r.installation_id, r);
    }
  }

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <div className="page-title">Dashboard</div>
        <div className="page-subtitle">A clear view of runs, cost, and agents.</div>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Runs Today"
          value={runsToday}
          className="shadow-[0_1px_2px_rgba(0,0,0,0.04),0_10px_26px_rgba(0,0,0,0.08)]"
        />
        <MetricCard
          label="Cost Today"
          value={costToday}
          format={(n) => `$${n.toFixed(2)}`}
          className="shadow-[0_1px_2px_rgba(0,0,0,0.04),0_10px_26px_rgba(0,0,0,0.08)]"
        />
        <MetricCard
          label="Monthly Runs"
          value={monthlyRuns}
          className="shadow-[0_1px_2px_rgba(0,0,0,0.04),0_10px_26px_rgba(0,0,0,0.08)]"
        />
        <MetricCard
          label="Total Spend"
          value={totalSpend}
          format={(n) => `$${n.toFixed(2)}`}
          className="shadow-[0_1px_2px_rgba(0,0,0,0.04),0_10px_26px_rgba(0,0,0,0.08)]"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-[18px] font-medium text-foreground">Installed Agents</div>
              <div className="mt-1 text-sm text-foreground-secondary">What’s installed and ready to run.</div>
            </div>
            <Button asChild variant="secondary" size="sm">
              <Link href="/agents">Agents</Link>
            </Button>
          </div>

          <div className="mt-6 space-y-3">
            {installations.length === 0 ? (
              <EmptyState
                icon={<Bot className="mx-auto" />}
                title="Start by installing your first agent"
                description="Install your first agent to start automating workflows."
                action={
                  <Button asChild>
                    <Link href="/deployments">Deployments</Link>
                  </Button>
                }
              />
            ) : (
              installations.slice(0, 8).map((inst) => {
                const last = lastRunByInstallation.get(inst.installation_id);
                const lastRunText = last?.created_at ? `Last run: ${last.created_at}` : "No runs yet";
                const status = (inst.status || "active").toString();
                return (
                  <div
                    key={inst.installation_id}
                    className="flex items-center justify-between gap-4 rounded-xl bg-background p-4 transition duration-200 hover:-translate-y-[1px] hover:shadow-soft"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-foreground">{inst.agent_name}</div>
                      <div className="mt-1 text-sm text-foreground-secondary">{lastRunText}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-elevated px-3 py-1 text-sm text-foreground-secondary">
                        {status}
                      </div>
                      <Button asChild size="sm">
                        <Link href={`/installations/${inst.installation_id}/configure`}>Configure</Link>
                      </Button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>

        <Card className="p-6">
          <div className="text-[18px] font-medium text-foreground">Activity</div>
          <div className="mt-1 text-sm text-foreground-secondary">Recent runs and status.</div>

          <div className="mt-6">
            {recentRuns.length === 0 ? (
              <div className="text-sm text-foreground-secondary">No activity yet.</div>
            ) : (
              <div className="overflow-hidden rounded-2xl border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="bg-elevated text-foreground-secondary">
                    <tr>
                      <th className="px-4 py-3 font-medium">Agent</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentRuns.slice(0, 6).map((r) => (
                      <tr key={`${r.run_id}-${r.task_id}`} className="border-t border-border hover:bg-card-hover">
                        <td className="px-4 py-3 font-medium text-foreground">{r.agent_name}</td>
                        <td className="px-4 py-3 text-foreground-secondary">{r.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
