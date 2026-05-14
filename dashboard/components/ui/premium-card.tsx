"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface PremiumCardProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

export function PremiumCard({
  children,
  className,
  delay = 0,
}: PremiumCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={cn(
        "rounded-xl border border-border bg-card p-6 shadow-soft transition-all duration-200",
        "hover:border-border/80 card-hover-lift",
        className
      )}
    >
      {children}
    </motion.div>
  );
}
