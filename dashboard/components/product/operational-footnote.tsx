"use client";

import { useState } from "react";
import { ChevronDown, RefreshCw } from "lucide-react";
import { DEGRADED_CONNECTIVITY } from "@/lib/trust-copy";

const DEV_HINTS = process.env.NEXT_PUBLIC_DEV_HINTS === "1";

/**
 * Lowest visual priority — below success content. Informational only.
 */
export function OperationalFootnote({
  message = DEGRADED_CONNECTIVITY.footnote,
  onRetry,
  diagnostic,
}: {
  message?: string;
  onRetry?: () => void;
  /** Only shown when NEXT_PUBLIC_DEV_HINTS=1 */
  diagnostic?: string;
}) {
  const [showDev, setShowDev] = useState(false);
  const devDetail = DEV_HINTS ? diagnostic : undefined;

  return (
    <div className="border-t border-white/[0.04] pt-5" role="status">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="max-w-2xl text-[11px] leading-relaxed text-neutral-600">{message}</p>
        {onRetry ? (
          <button
            type="button"
            className="inline-flex items-center gap-1 text-[11px] text-neutral-500 transition-colors hover:text-neutral-400"
            onClick={onRetry}
          >
            <RefreshCw className="h-3 w-3" />
            Retry sync
          </button>
        ) : null}
      </div>
      {devDetail ? (
        <>
          <button
            type="button"
            className="mt-2 flex items-center gap-1 text-[10px] text-neutral-700 hover:text-neutral-500"
            onClick={() => setShowDev((v) => !v)}
          >
            <ChevronDown
              className={`h-3 w-3 transition-transform ${showDev ? "rotate-180" : ""}`}
            />
            Technical details
          </button>
          {showDev ? (
            <p className="mt-1.5 rounded bg-neutral-900/50 px-2 py-1.5 font-mono text-[10px] text-neutral-600">
              {devDetail}
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
