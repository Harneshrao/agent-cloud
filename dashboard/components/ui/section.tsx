"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface SectionProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  className?: string;
  children?: ReactNode;
}

export function Section({ title, subtitle, action, className, children }: SectionProps) {
  return (
    <section className={cn("grid gap-6", className)}>
      <header className="flex items-start justify-between gap-4">
        <div className="grid gap-4">
          <h2 className="text-lg font-medium text-foreground">{title}</h2>
          {subtitle ? (
            <p className="text-sm text-foreground-secondary">{subtitle}</p>
          ) : null}
        </div>
        {action ? <div>{action}</div> : null}
      </header>
      {children ? <div className="grid gap-6">{children}</div> : null}
    </section>
  );
}

