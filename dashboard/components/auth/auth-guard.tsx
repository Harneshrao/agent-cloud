"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { getAccessToken, getRefreshToken, refreshAccessToken, startTokenRefreshTimer } from "@/lib/auth";

function LoadingSession() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#F3F2EF]" aria-busy="true">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#0A66C2] border-t-transparent" />
      <p className="text-sm text-foreground-secondary">Loading session...</p>
    </div>
  );
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const timerStarted = useRef(false);

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      const accessToken = getAccessToken();
      const refreshToken = getRefreshToken();

      if (accessToken) {
        if (!cancelled) setReady(true);
        return;
      }

      if (refreshToken) {
        try {
          await refreshAccessToken();
          if (!cancelled) setReady(true);
          return;
        } catch {
          if (!cancelled) router.replace("/login");
          return;
        }
      }

      if (!cancelled) router.replace("/login");
    };

    init();
    return () => {
      cancelled = true;
    };
  }, [router]);

  // Proactive token refresh: start 10-minute timer once when session is ready
  useEffect(() => {
    if (!ready || timerStarted.current) return;
    timerStarted.current = true;
    startTokenRefreshTimer();
  }, [ready]);

  if (!ready) {
    return <LoadingSession />;
  }

  return <>{children}</>;
}
