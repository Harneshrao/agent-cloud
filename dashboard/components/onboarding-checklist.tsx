"use client";

import Link from "next/link";
import { CheckCircle2, Circle } from "lucide-react";
import { GlassCard } from "@/components/product/glass-card";

const STEPS = [
  { id: "project", label: "Create a project", href: "/projects" },
  { id: "deploy", label: "Upload & deploy agent ZIP", href: "/deployments" },
  { id: "run", label: "Run a task", href: "/deployments" },
  { id: "logs", label: "View run logs", href: "/runs" },
  { id: "keys", label: "Create an API key", href: "/api-keys" },
] as const;

export function OnboardingChecklist({
  hasProject,
  hasDeployment,
}: {
  hasProject: boolean;
  hasDeployment: boolean;
}) {
  const done = {
    project: hasProject,
    deploy: hasDeployment,
    run: hasDeployment,
    logs: hasDeployment,
    keys: false,
  };

  return (
    <GlassCard className="border-primary/20 bg-primary/5 p-6">
      <h2 className="text-lg font-semibold text-foreground">15-minute quickstart</h2>
      <p className="mt-1 text-sm text-neutral-400">
        Deploy your first agent, run a task, and read logs — no founder call required.
      </p>
      <ol className="mt-4 space-y-3">
        {STEPS.map((step) => {
          const complete = done[step.id as keyof typeof done];
          return (
            <li key={step.id} className="flex items-start gap-3">
              {complete ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              ) : (
                <Circle className="mt-0.5 h-5 w-5 shrink-0 text-neutral-500" />
              )}
              <div>
                <Link href={step.href} className="text-sm font-medium text-foreground hover:text-primary">
                  {step.label}
                </Link>
              </div>
            </li>
          );
        })}
      </ol>
      <p className="mt-4 text-xs text-neutral-500">
        Sample agents in <code className="rounded bg-black/20 px-1">agents/sample_echo</code>,{" "}
        <code className="rounded bg-black/20 px-1">sample_fail</code>,{" "}
        <code className="rounded bg-black/20 px-1">sample_slow</code>. Full steps:{" "}
        <code className="rounded bg-black/20 px-1">QUICKSTART.md</code> at repo root.
      </p>
    </GlassCard>
  );
}
