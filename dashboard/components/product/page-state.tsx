"use client";

import type { ReactNode } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { PlatformAlert } from "@/components/product/platform-alert";
import type { PlatformErrorView } from "@/lib/platform-errors";

export function PageLoader({ className }: { className?: string }) {
  return <Skeleton className={className ?? "h-64 rounded-2xl"} />;
}

/**
 * Unified async page wrapper: loading skeleton, error panel, or content.
 */
export function PageState({
  loading,
  error,
  onRetry,
  children,
  loaderClassName,
}: {
  loading?: boolean;
  error?: string | PlatformErrorView | null;
  onRetry?: () => void;
  children: ReactNode;
  loaderClassName?: string;
}) {
  if (loading) {
    return <PageLoader className={loaderClassName} />;
  }
  if (error) {
    return <PlatformAlert error={error} onRetry={onRetry} />;
  }
  return <>{children}</>;
}
