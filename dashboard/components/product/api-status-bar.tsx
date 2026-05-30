"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { usePlatformState } from "@/context/platform-state";
import { useDevDeepHealth } from "@/hooks/use-dev-deep-health";
import { DEGRADED_CONNECTIVITY } from "@/lib/trust-copy";

const DEV_HINTS = process.env.NEXT_PUBLIC_DEV_HINTS === "1";

/**
 * Whisper-thin global strip — hidden on Deployments (page shows footnote below success).
 * In dev, also warns when deep health shows infra issues (Redis, workers, etc.).
 */
export function ApiStatusBar() {
  const pathname = usePathname() ?? "";
  const { apiReady, apiChecked, checkHealth } = usePlatformState();
  const { degraded: infraDegraded, issues, refresh: refreshDeep } = useDevDeepHealth(DEV_HINTS);
  const [retrying, setRetrying] = useState(false);

  const showApiStrip = apiChecked && !apiReady && !pathname.startsWith("/deployments");
  const showDevStrip = DEV_HINTS && infraDegraded && !pathname.startsWith("/deployments");

  if (!showApiStrip && !showDevStrip) return null;

  const onRetry = async () => {
    setRetrying(true);
    try {
      await Promise.all([checkHealth(), refreshDeep()]);
    } finally {
      setRetrying(false);
    }
  };

  const message = showApiStrip
    ? DEGRADED_CONNECTIVITY.strip
    : `Dev infra: ${issues.slice(0, 2).join(" · ")} — run dev_doctor.py`;

  return (
    <div
      className="flex items-center justify-end gap-3 border-b border-white/[0.03] px-8 py-1"
      role="status"
    >
      <span className="flex-1 text-[10px] text-neutral-600">{message}</span>
      <button
        type="button"
        className="inline-flex items-center gap-1 text-[10px] text-neutral-600 hover:text-neutral-500"
        disabled={retrying}
        onClick={onRetry}
      >
        <RefreshCw className={`h-2.5 w-2.5 ${retrying ? "animate-spin" : ""}`} />
        {retrying ? "…" : "Retry"}
      </button>
    </div>
  );
}
