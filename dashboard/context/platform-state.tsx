"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { checkApiHealth } from "@/lib/api";

const POLL_WHEN_DOWN_MS = 3000;
const POLL_WHEN_UP_MS = 30000;

type PlatformStateValue = {
  apiReady: boolean;
  apiChecked: boolean;
  checkHealth: () => Promise<boolean>;
};

const PlatformStateContext = createContext<PlatformStateValue | null>(null);

export function PlatformStateProvider({ children }: { children: React.ReactNode }) {
  const [apiReady, setApiReady] = useState(true);
  const [apiChecked, setApiChecked] = useState(false);

  const checkHealth = useCallback(async () => {
    const ok = await checkApiHealth();
    setApiReady(ok);
    setApiChecked(true);
    return ok;
  }, []);

  useEffect(() => {
    checkHealth();
    const intervalMs = apiReady ? POLL_WHEN_UP_MS : POLL_WHEN_DOWN_MS;
    const id = setInterval(checkHealth, intervalMs);
    return () => clearInterval(id);
  }, [checkHealth, apiReady]);

  const value = useMemo(
    () => ({ apiReady, apiChecked, checkHealth }),
    [apiReady, apiChecked, checkHealth]
  );

  return (
    <PlatformStateContext.Provider value={value}>
      {children}
    </PlatformStateContext.Provider>
  );
}

export function usePlatformState() {
  const ctx = useContext(PlatformStateContext);
  if (!ctx) {
    throw new Error("usePlatformState must be used within PlatformStateProvider");
  }
  return ctx;
}
