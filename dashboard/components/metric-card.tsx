"use client";

import { ReactNode } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { AnimatedNumber } from "@/components/animated-number";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  description?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
  /** When true and value is a number, animate value changes */
  animate?: boolean;
}

export function MetricCard({
  title,
  value,
  icon,
  description,
  trend,
  className,
  animate = true,
}: MetricCardProps) {
  const isNumeric = typeof value === "number" && animate;
  return (
    <Card className={cn("group overflow-hidden transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_12px_40px_-8px_rgba(0,0,0,0.45)]", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <span className="text-sm font-medium text-neutral-400">{title}</span>
        {icon && (
          <span className="rounded-lg bg-accent/10 p-2 text-accent transition-transform duration-200 group-hover:scale-105">
            {icon}
          </span>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tabular-nums">
          {isNumeric ? (
            <AnimatedNumber value={value} />
          ) : (
            value
          )}
        </div>
        {description && (
          <p className="mt-1 text-xs text-neutral-500">{description}</p>
        )}
        {trend && (
          <span
            className={cn(
              "mt-1 inline-block text-xs font-medium",
              trend === "up" && "text-emerald-400",
              trend === "down" && "text-red-400",
              trend === "neutral" && "text-neutral-500"
            )}
          >
            {trend === "up" && "↑"}
            {trend === "down" && "↓"}
            {trend === "neutral" && "→"}
          </span>
        )}
      </CardContent>
    </Card>
  );
}
