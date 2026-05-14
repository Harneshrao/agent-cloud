"use client";

import { useEffect, useState, useCallback } from "react";
import { SystemMetrics } from "@/components/system/system-metrics";
import {
  fetchSystemWorkers,
  fetchSystemQueue,
  fetchSystemContainers,
} from "@/lib/api";
import type { WorkerInfo, QueueInfo, ContainerInfo } from "@/types";

export default function SystemHealthPage() {
  const [workers, setWorkers] = useState<WorkerInfo[] | null>(null);
  const [queue, setQueue] = useState<QueueInfo | null>(null);
  const [containers, setContainers] = useState<ContainerInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [w, q, c] = await Promise.all([
        fetchSystemWorkers(),
        fetchSystemQueue(),
        fetchSystemContainers(),
      ]);
      setWorkers(w.workers);
      setQueue(q);
      setContainers(c);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load system data");
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">System Health</h1>
        <p className="text-neutral-400 mt-1">Workers, queue, and container pool</p>
      </div>

      <SystemMetrics
        workers={workers}
        queue={queue}
        containers={containers}
        error={error}
        onRetry={load}
      />
    </div>
  );
}
