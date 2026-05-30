"use client";

import { useState } from "react";
import { AlertCircle, ChevronDown, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  type PlatformErrorView,
  toPlatformError,
} from "@/lib/platform-errors";
import { PlatformNotice } from "@/components/product/platform-notice";

const DEV_HINTS = process.env.NEXT_PUBLIC_DEV_HINTS === "1";

/**
 * Attention-needed issues (validation, blocking errors).
 * Degraded/offline uses calm PlatformNotice instead.
 */
export function PlatformAlert({
  error,
  onRetry,
  className,
}: {
  error: PlatformErrorView | string | unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const view =
    typeof error === "object" && error !== null && "kind" in error
      ? (error as PlatformErrorView)
      : toPlatformError(error);

  if (view.kind === "degraded" || view.tone === "calm") {
    return <PlatformNotice error={view} onRetry={onRetry} className={className} />;
  }

  const [showDiagnostic, setShowDiagnostic] = useState(false);

  return (
    <div
      className={`rounded-xl border border-amber-500/25 bg-amber-500/8 px-4 py-3 text-sm text-amber-50 ${
        className ?? ""
      }`}
      role="alert"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex gap-3">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400/90" />
          <div>
            <p className="font-medium">{view.title}</p>
            <p className="mt-1 text-amber-100/90">{view.message}</p>
            {view.dataSafe ? (
              <p className="mt-2 text-xs text-amber-200/60">Your data is safe.</p>
            ) : null}
            {view.hint ? (
              <p className="mt-1 text-xs text-amber-200/70">{view.hint}</p>
            ) : null}
            {DEV_HINTS && view.diagnostic ? (
              <button
                type="button"
                className="mt-2 flex items-center gap-1 text-xs text-amber-200/50 hover:text-amber-100"
                onClick={() => setShowDiagnostic((v) => !v)}
              >
                <ChevronDown
                  className={`h-3.5 w-3.5 transition-transform ${showDiagnostic ? "rotate-180" : ""}`}
                />
                {showDiagnostic ? "Hide details" : "Technical details"}
              </button>
            ) : null}
            {showDiagnostic && view.diagnostic ? (
              <p className="mt-2 rounded-lg bg-black/15 px-3 py-2 font-mono text-xs text-amber-100/70">
                {view.diagnostic}
              </p>
            ) : null}
          </div>
        </div>
        {view.retryable && onRetry ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="shrink-0 border-amber-500/35 text-amber-50 hover:bg-amber-500/15"
            onClick={onRetry}
          >
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            Retry
          </Button>
        ) : null}
      </div>
    </div>
  );
}
