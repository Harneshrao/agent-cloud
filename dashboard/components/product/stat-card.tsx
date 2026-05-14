"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  sub,
  className,
}: {
  label: string;
  value: string | number;
  sub?: string;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.25 }}
      className={cn(
        "rounded-2xl border border-white/5 bg-card/60 backdrop-blur p-5",
        "transition-colors hover:border-white/10",
        className
      )}
    >
      <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-foreground tabular-nums">{value}</p>
      {sub != null && <p className="mt-0.5 text-sm text-neutral-500">{sub}</p>}
    </motion.div>
  );
}
