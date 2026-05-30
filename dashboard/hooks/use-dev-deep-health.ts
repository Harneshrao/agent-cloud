"use client";

import { useCallback, useEffect, useState } from "react";
import { getApiBaseUrl } from "@/lib/api";

type DeepHealth = {
  status: string;
  components?: Record<string, string>;
};

/**
 * Poll GET /health?deep=1 in dev — surfaces infra issues before they look like product bugs.
 */
export function useDevDeepHealth(enabled: boolean) {
  const [health, setHealth] = useState<DeepHealth | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    const base = getApiBaseUrl();
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`${base}/health?deep=1`, {
        signal: controller.signal,
        cache: "no-store",
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        setHealth((await res.json()) as DeepHealth);
      } else {
        setHealth({ status: "error", components: { api: `HTTP ${res.status}` } });
      }
    } catch {
      setHealth({ status: "error", components: { api: "unreachable" } });
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [enabled, refresh]);

  const issues =
    health?.components &&
    Object.entries(health.components)
      .filter(([, v]) => v !== "ok")
      .map(([k, v]) => `${k}: ${v}`);

  return {
    degraded: Boolean(issues?.length) || health?.status === "degraded",
    issues: issues ?? [],
    refresh,
  };
}
