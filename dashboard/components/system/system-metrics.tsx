"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { WorkerTable } from "@/components/worker-table";
import { ContainerUtilization } from "@/components/container-utilization";
import {
  fetchSystemWorkers,
  fetchSystemQueue,
  fetchSystemContainers,
} from "@/lib/api";
import type { WorkerInfo, QueueInfo, ContainerInfo } from "@/types";
import { Inbox, AlertTriangle, Users } from "lucide-react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

const QUEUE_ALERT_THRESHOLD = 20;
const CONTAINER_SATURATION_THRESHOLD = 0.9;
const WORKER_OFFLINE_SEC = 60;

interface SystemMetricsProps {
  workers: WorkerInfo[] | null;
  queue: QueueInfo | null;
  containers: ContainerInfo | null;
  error: string | null;
  onRetry?: () => void;
}

export function SystemMetrics({
  workers,
  queue,
  containers,
  error,
  onRetry,
}: SystemMetricsProps) {
  const [queueHistory, setQueueHistory] = useState<{ time: string; length: number }[]>([]);

  useEffect(() => {
    if (queue == null) return;
    const now = new Date();
    const t = now.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setQueueHistory((prev) => [...prev.slice(-29), { time: t, length: queue.queue_length }]);
  }, [queue?.queue_length]);

  const queueAlert = queue != null && queue.queue_length > QUEUE_ALERT_THRESHOLD;
  const workerOffline =
    workers != null &&
    workers.some((w) => {
      if (!w.last_seen) return true;
      const seen = new Date(w.last_seen).getTime();
      return Date.now() - seen > WORKER_OFFLINE_SEC * 1000;
    });
  const totalContainers =
    containers != null ? containers.containers_idle + containers.containers_busy : 0;
  const utilization =
    totalContainers > 0 && containers
      ? containers.containers_busy / totalContainers
      : 0;
  const containerSaturation = utilization >= CONTAINER_SATURATION_THRESHOLD;

  const alerts = [
    queueAlert && { type: "queue" as const, message: `Queue backlog (${queue?.queue_length}) above ${QUEUE_ALERT_THRESHOLD}` },
    workerOffline && { type: "worker" as const, message: "One or more workers have not reported recently" },
    containerSaturation && { type: "container" as const, message: "Container pool utilization is high" },
  ].filter(Boolean) as { type: string; message: string }[];

  return (
    <div className="space-y-8 animate-fade-in">
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 flex items-center justify-between">
          <span>{error}</span>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="text-red-300 hover:text-red-200 underline"
            >
              Retry
            </button>
          )}
        </div>
      )}

      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((a, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200"
            >
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {a.message}
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {queue != null ? (
          <Card className="transition-all duration-300 hover:shadow-soft">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Inbox className="h-4 w-4" />
                Queue backlog
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold tabular-nums">{queue.queue_length}</p>
              <p className="text-sm text-neutral-500 mt-1">Key: {queue.queue_key}</p>
            </CardContent>
          </Card>
        ) : (
          <Skeleton className="h-[120px] rounded-2xl" />
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {workers !== null ? (
          <WorkerTable workers={workers} />
        ) : (
          <Skeleton className="h-[320px] rounded-2xl" />
        )}
        {containers !== null ? (
          <ContainerUtilization data={containers} />
        ) : (
          <Skeleton className="h-[320px] rounded-2xl" />
        )}
      </div>

      {queueHistory.length > 0 && (
        <Card className="transition-all duration-300 hover:shadow-soft">
          <CardHeader>
            <CardTitle className="text-base">Queue backlog over time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={queueHistory} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <XAxis dataKey="time" stroke="#666" fontSize={10} tickLine={false} />
                  <YAxis stroke="#666" fontSize={10} tickLine={false} width={28} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1a1a1a",
                      border: "1px solid #2a2a2a",
                      borderRadius: "12px",
                    }}
                  />
                  <Bar dataKey="length" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {workers != null && workers.length > 0 && (
        <Card className="transition-all duration-300 hover:shadow-soft">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Users className="h-4 w-4" />
              Worker load
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {workers.map((w) => {
                const tasks = w.tasks_running ?? 0;
                const pct = Math.min(100, tasks * 25);
                return (
                  <div key={w.worker_id} className="flex items-center gap-3 min-w-[200px]">
                    <span className="font-mono text-sm text-neutral-400 truncate max-w-[120px]">
                      {w.worker_id}
                    </span>
                    <div className="flex-1 h-2 rounded-full bg-border overflow-hidden">
                      <div
                        className="h-full rounded-full bg-accent transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs tabular-nums text-neutral-500">{tasks}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
