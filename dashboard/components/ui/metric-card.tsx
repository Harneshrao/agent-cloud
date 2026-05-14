"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

function useAnimatedNumber(value: number, durationMs = 260) {
  const [display, setDisplay] = useState(value);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const start = performance.now();
    const from = display;
    const to = value;

    if (!Number.isFinite(from) || !Number.isFinite(to) || from === to) {
      setDisplay(value);
      return;
    }

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      setDisplay(from + (to - from) * eased);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return display;
}

export function MetricCard({
  label,
  value,
  format,
  className,
}: {
  label: string;
  value: number;
  format?: (n: number) => string;
  className?: string;
}) {
  const animated = useAnimatedNumber(value);
  const text = useMemo(() => (format ? format(animated) : Math.round(animated).toString()), [animated, format]);

  return (
    <Card
      className={cn(
        "p-6 transition-all duration-200 ease-in-out hover:-translate-y-[2px]",
        className
      )}
    >
      <div className="text-[13px] text-foreground-secondary">{label}</div>
      <div className="mt-5 text-[38px] font-semibold tracking-tight text-foreground tabular-nums leading-[1.02]">
        {text}
      </div>
    </Card>
  );
}
