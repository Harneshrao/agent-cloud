"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function EmptyState({
  icon: Icon,
  title,
  description,
  why,
  actionLabel,
  actionHref,
  onAction,
  secondaryLabel,
  secondaryHref,
}: {
  icon?: LucideIcon;
  title: string;
  description: string;
  why?: string;
  actionLabel: string;
  actionHref?: string;
  onAction?: () => void;
  secondaryLabel?: string;
  secondaryHref?: string;
}) {
  const actionButton = onAction ? (
    <Button type="button" onClick={onAction}>
      {actionLabel}
    </Button>
  ) : actionHref ? (
    <Button asChild>
      <Link href={actionHref}>{actionLabel}</Link>
    </Button>
  ) : null;

  return (
    <div className="flex flex-col items-center px-8 py-14 text-center">
      {Icon ? (
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Icon className="h-7 w-7" />
        </div>
      ) : null}
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-neutral-400">{description}</p>
      {why ? (
        <p className="mt-3 max-w-md text-xs text-neutral-500">{why}</p>
      ) : null}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        {actionButton}
        {secondaryHref && secondaryLabel ? (
          <Button variant="outline" asChild>
            <Link href={secondaryHref}>{secondaryLabel}</Link>
          </Button>
        ) : null}
      </div>
    </div>
  );
}
