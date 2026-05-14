"use client";

import { useEffect, useState, useRef } from "react";
import type { SystemMetrics } from "@/types";
import { fetchSystemMetrics } from "@/lib/api";
import { getSystemStreamUrl, type MetricsUpdateEvent } from "@/lib/stream";

const POLL_FALLBACK_MS = 5000;

export function useSystemStream(): {
  metrics: SystemMetrics | null;
  error: string | null;
  isLive: boolean;
} {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(false);
  const fallbackRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let mounted = true;
    const url = getSystemStreamUrl();

    const tryFetch = async () => {
      try {
        const data = await fetchSystemMetrics();
        if (mounted) setMetrics(data);
      } catch (e) {
        if (mounted) setError(e instanceof Error ? e.message : "Failed to load metrics");
      }
    };

    tryFetch();

    try {
      const es = new EventSource(url);
      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as MetricsUpdateEvent;
          if (parsed.type === "metrics_update" && parsed.data && mounted) {
            setIsLive(true);
            setMetrics((prev) => {
              const next = { ...(prev || {}), ...parsed.data } as SystemMetrics;
              if (typeof next.queue_length !== "number") next.queue_length = prev?.queue_length ?? 0;
              if (typeof next.workers_active !== "number") next.workers_active = prev?.workers_active ?? 0;
              if (typeof next.containers_idle !== "number") next.containers_idle = prev?.containers_idle ?? 0;
              if (typeof next.containers_busy !== "number") next.containers_busy = prev?.containers_busy ?? 0;
              if (typeof next.tasks_running !== "number") next.tasks_running = prev?.tasks_running ?? 0;
              if (typeof next.tasks_failed_last_hour !== "number") next.tasks_failed_last_hour = prev?.tasks_failed_last_hour ?? 0;
              return next;
            });
          }
        } catch (_) {}
      };
      es.onerror = () => {
        es.close();
        if (mounted) setIsLive(false);
      };
      return () => {
        es.close();
      };
    } catch (_) {
      fallbackRef.current = setInterval(tryFetch, POLL_FALLBACK_MS);
    }

    fallbackRef.current = setInterval(tryFetch, POLL_FALLBACK_MS);
    return () => {
      mounted = false;
      if (fallbackRef.current) clearInterval(fallbackRef.current);
      fallbackRef.current = null;
    };
  }, []);

  return { metrics, error, isLive };
}
