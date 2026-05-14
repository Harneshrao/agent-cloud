"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function GlassCard({
  children,
  className,
  ...props
}: React.ComponentProps<typeof motion.div>) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn(
        "rounded-2xl border border-white/5 bg-card/80 backdrop-blur-xl shadow-[0_4px_24px_-4px_rgba(0,0,0,0.3)]",
        "transition-all duration-300 hover:border-white/10 hover:shadow-[0_12px_40px_-8px_rgba(0,0,0,0.4)]",
        className
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
}
