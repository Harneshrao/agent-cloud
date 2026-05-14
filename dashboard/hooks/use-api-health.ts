"use client";

import { useCallback, useEffect, useState } from "react";
import { checkApiHealth } from "@/lib/api";

const HEALTH_CHECK_INTERVAL_MS = 3000;

/**
 * Polls GET /health until the API is reachable.
 * When running in browser: checks on mount, then every 3s while unavailable.
 * When API becomes ready, stops polling and exposes apiReady true.
 */
export function useApiHealth() {
  const [apiReady, setApiReady] = useState(false);

  const check = useCallback(async () => {
    const ok = await checkApiHealth();
    setApiReady(ok);
    return ok;
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    check();

    const interval = setInterval(() => {
      check().then((ok) => {
        if (ok) clearInterval(interval);
      });
    }, HEALTH_CHECK_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [check]);

  return { apiReady, checkHealth: check };
}
