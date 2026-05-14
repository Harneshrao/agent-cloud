"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function AuthCard({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "w-full max-w-[400px] rounded-xl border border-gray-200 bg-white p-8 shadow-[0_2px_8px_rgba(0,0,0,0.06)]",
        className
      )}
    >
      {children}
    </motion.div>
  );
}
