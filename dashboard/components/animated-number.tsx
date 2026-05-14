"use client";

import { useEffect, useState, useRef } from "react";
import { cn } from "@/lib/utils";

const DURATION_MS = 400;

function easeOutQuart(t: number): number {
  return 1 - Math.pow(1 - t, 4);
}

interface AnimatedNumberProps {
  value: number;
  className?: string;
  format?: (n: number) => string;
}

export function AnimatedNumber({
  value,
  className,
  format = (n) => String(Math.round(n)),
}: AnimatedNumberProps) {
  const [display, setDisplay] = useState(value);
  const prevRef = useRef(value);
  const rafRef = useRef<number>(0);
  const startRef = useRef(0);

  useEffect(() => {
    const prev = prevRef.current;
    if (prev === value) return;
    prevRef.current = value;
    const start = performance.now();
    const diff = value - prev;

    const tick = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(elapsed / DURATION_MS, 1);
      const eased = easeOutQuart(t);
      setDisplay(prev + diff * eased);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [value]);

  return (
    <span className={cn("tabular-nums transition-opacity duration-150", className)}>
      {format(display)}
    </span>
  );
}
