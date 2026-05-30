"use client";

import { useState } from "react";
import { ChevronDown, Info, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  type PlatformErrorView,
  toPlatformError,
} from "@/lib/platform-errors";

const DEV_HINTS = process.env.NEXT_PUBLIC_DEV_HINTS === "1";

/**
 * Calm notice — use `whisper` on pages where success state must dominate.
 */
export function PlatformNotice({
  error,
  onRetry,
  variant = "default",
  className,
}: {
  error: PlatformErrorView | string | unknown;
  onRetry?: () => void;
  /** whisper = single line, no box (legacy compact maps to whisper) */
  variant?: "default" | "whisper" | "compact";
  className?: string;
}) {
  const view =
    typeof error === "object" && error !== null && "kind" in error
      ? (error as PlatformErrorView)
      : toPlatformError(error);

  const isWhisper = variant === "whisper" || variant === "compact";
  const devDetail = DEV_HINTS ? view.diagnostic : undefined;
  const [showDev, setShowDev] = useState(false);

  if (isWhisper) {
    const line =
      view.kind === "degraded"
        ? view.message
        : `${view.title}. ${view.message}`;
    return (
      <p
        className={`text-[11px] leading-relaxed text-neutral-600 ${className ?? ""}`}
        role="status"
      >
        {line}
        {view.retryable && onRetry ? (
          <>
            {" "}
            <button
              type="button"
              className="text-neutral-500 underline-offset-2 hover:text-neutral-400 hover:underline"
              onClick={onRetry}
            >
              Retry
            </button>
          </>
        ) : null}
      </p>
    );
  }

  return (
    <div
      className={`rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 text-sm text-neutral-400 ${
        className ?? ""
      }`}
      role="status"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex gap-2.5">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-neutral-500" />
          <div>
            <p className="text-sm text-neutral-300">{view.title}</p>
            <p className="mt-1 text-xs text-neutral-500">{view.message}</p>
            {view.dataSafe ? (
              <p className="mt-1.5 text-[11px] text-neutral-600">Your data is safe.</p>
            ) : null}
            {devDetail ? (
              <>
                <button
                  type="button"
                  className="mt-2 flex items-center gap-1 text-[10px] text-neutral-600 hover:text-neutral-500"
                  onClick={() => setShowDev((v) => !v)}
                >
                  <ChevronDown
                    className={`h-3 w-3 transition-transform ${showDev ? "rotate-180" : ""}`}
                  />
                  Technical details
                </button>
                {showDev ? (
                  <p className="mt-1.5 rounded bg-neutral-900/60 px-2 py-1.5 font-mono text-[10px] text-neutral-600">
                    {devDetail}
                  </p>
                ) : null}
              </>
            ) : null}
          </div>
        </div>
        {view.retryable && onRetry ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 text-xs text-neutral-500"
            onClick={onRetry}
          >
            <RefreshCw className="mr-1.5 h-3 w-3" />
            Retry
          </Button>
        ) : null}
      </div>
    </div>
  );
}
