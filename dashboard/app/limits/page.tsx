"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchBillingSummary } from "@/lib/api";
import { GlassCard } from "@/components/product/glass-card";
import { Skeleton } from "@/components/ui/skeleton";

export default function LimitsPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchBillingSummary>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchBillingSummary();
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load limits");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const u = data?.usage;
  const lim = data?.limits;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">Limits & quotas</h1>
        <p className="mt-1 text-neutral-400">
          Plan: {data?.plan?.name ?? "—"} · What you have used vs what your plan allows.
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
        <>
          {(data?.warnings ?? []).length > 0 ? (
            <GlassCard className="border-amber-500/30 bg-amber-500/5 p-4">
              <p className="text-sm font-medium text-amber-200">Warnings</p>
              <ul className="mt-2 space-y-1 text-sm text-amber-100/80">
                {data?.warnings.map((w) => (
                  <li key={w.code}>
                    {w.message} <span className="text-neutral-500">({w.code})</span>
                  </li>
                ))}
              </ul>
            </GlassCard>
          ) : null}
          <div className="grid gap-4 md:grid-cols-2">
            <LimitRow
              label="Task runs (month)"
              used={u?.runs_enqueued}
              limit={lim?.monthly_run_limit}
            />
            <LimitRow
              label="Execution time (ms)"
              used={u?.execution_time_ms}
              limit={lim?.monthly_execution_time_limit_ms}
            />
            <LimitRow label="Deployments" used={u?.deployments} limit={lim?.max_deployments} />
            <LimitRow
              label="Artifact storage (MB)"
              used={u?.artifact_storage_mb}
              limit={lim?.max_artifact_storage_mb}
            />
            <LimitRow
              label="Concurrent runs"
              used={u?.concurrent_running}
              limit={lim?.max_concurrent_running}
            />
            <LimitRow label="Retries (month)" used={u?.retries} limit={lim?.max_retries_per_hour} />
          </div>
          <p className="text-sm text-neutral-500">
            Need more capacity?{" "}
            <Link href="/usage" className="text-primary hover:underline">
              View usage
            </Link>{" "}
            or upgrade plan (contact operator).
          </p>
        </>
      )}
    </div>
  );
}

function LimitRow({
  label,
  used,
  limit,
}: {
  label: string;
  used?: number;
  limit?: number | null;
}) {
  const pct =
    limit != null && limit > 0 && used != null ? Math.min(100, (used / limit) * 100) : null;
  return (
    <GlassCard className="p-4">
      <p className="text-sm text-neutral-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-foreground">
        {used ?? 0}
        {limit != null ? ` / ${limit}` : ""}
      </p>
      {pct != null ? (
        <div className="mt-2 h-1.5 rounded-full bg-white/10">
          <div
            className="h-1.5 rounded-full bg-primary"
            style={{ width: `${pct}%` }}
          />
        </div>
      ) : null}
    </GlassCard>
  );
}
