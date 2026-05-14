"use client";

import { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: ReactNode;
  change?: string;
  className?: string;
}

export function StatCard({ label, value, change, className }: StatCardProps) {
  return (
    <Card className={cn("p-5", className)}>
      <CardContent className="p-0">
        <div className="grid gap-4">
          <div className="flex items-center justify-between gap-4">
            <div className="text-sm text-foreground-secondary">{label}</div>
            {change ? (
              <div className="rounded-xl bg-primary-soft px-3 py-1 text-sm font-medium text-primary">
                {change}
              </div>
            ) : null}
          </div>
          <div className="text-2xl font-semibold text-foreground tabular-nums">{value}</div>
        </div>
      </CardContent>
    </Card>
  );
}

