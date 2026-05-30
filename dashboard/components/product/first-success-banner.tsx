"use client";

import Link from "next/link";
import { CheckCircle2, Circle, Rocket } from "lucide-react";
import { useOnboardingProgress } from "@/hooks/use-onboarding-progress";
import { useActiveProject } from "@/context/active-project";
import { usePathname } from "next/navigation";

const STEPS = [
  { id: "project" as const, label: "Project", href: "/projects" },
  { id: "deployed" as const, label: "Deploy", href: "/deployments" },
  { id: "ran" as const, label: "Run", href: "/deployments" },
  { id: "viewed_logs" as const, label: "Trace", href: "/runs" },
  { id: "api_key" as const, label: "API key", href: "/api-keys" },
];

export function FirstSuccessBanner({ className }: { className?: string }) {
  const pathname = usePathname();
  const { hasProject } = useActiveProject();
  const progress = useOnboardingProgress();
  const doneCount = STEPS.filter((s) => progress[s.id]).length;
  if (doneCount >= STEPS.length) return null;

  const onDeploymentsWithDeploy = pathname === "/deployments" && progress.deployed;
  const compact = onDeploymentsWithDeploy || doneCount >= 2;

  const nextStep = STEPS.find((s) => !progress[s.id]);

  return (
    <div
      className={`rounded-xl border border-white/8 bg-white/[0.02] ${
        compact ? "px-4 py-3" : "p-5"
      } ${className ?? ""}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className={`flex shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary ${
              compact ? "h-8 w-8" : "h-10 w-10"
            }`}
          >
            <Rocket className={compact ? "h-4 w-4" : "h-5 w-5"} />
          </div>
          <div>
            <p className={`font-medium text-foreground ${compact ? "text-sm" : "text-base"}`}>
              {compact ? "Setup progress" : "Your first success loop"}
            </p>
            <p className="text-xs text-neutral-500">
              {doneCount} of {STEPS.length} complete
              {nextStep ? ` · Next: ${nextStep.label}` : ""}
            </p>
          </div>
        </div>
        {nextStep && !onDeploymentsWithDeploy ? (
          <Link
            href={nextStep.href}
            className="shrink-0 rounded-lg bg-primary/90 px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary"
          >
            Continue
          </Link>
        ) : null}
      </div>
      {!compact ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {STEPS.map((step) => {
            const done = progress[step.id];
            return (
              <Link
                key={step.id}
                href={step.href}
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                  done
                    ? "bg-primary/15 text-primary"
                    : "text-neutral-500 hover:bg-white/5"
                }`}
              >
                {done ? (
                  <CheckCircle2 className="h-3 w-3" />
                ) : (
                  <Circle className="h-3 w-3" />
                )}
                {step.label}
              </Link>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
