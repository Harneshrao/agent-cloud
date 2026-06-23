"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { ArrowRight, KeyRound, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/product/glass-card";
import { SuccessBanner } from "@/components/product/success-banner";
import { ExecutionStarting } from "@/components/product/execution-starting";
import { FeedbackPrompt } from "@/components/product/feedback-prompt";
import { ACTIVATION_COPY, NEXT_STEP, SUCCESS_MESSAGES } from "@/lib/trust-copy";
import type { DeploymentRecord, TaskListItem } from "@/types";
import { deploymentStatusLabel } from "@/lib/trust-copy";
import { trackDeployWithoutRunView, trackRunCtaClicked } from "@/lib/analytics";
import { useActiveProject } from "@/context/active-project";
import { taskTraceHref } from "@/lib/trace-navigation";

export function PostDeployPanel({
  deployment,
  recentTasks,
  running,
  onRunFirst,
}: {
  deployment: DeploymentRecord;
  recentTasks: TaskListItem[];
  running: boolean;
  onRunFirst: () => void;
}) {
  const { projectId } = useActiveProject();
  const isActive = deployment.status === "active";
  const hasCompletedRun = recentTasks.some((t) => t.status === "completed");
  const hasAnyRun = recentTasks.length > 0;
  const trackedGap = useRef(false);

  useEffect(() => {
    if (isActive && !hasAnyRun && !trackedGap.current) {
      trackedGap.current = true;
      trackDeployWithoutRunView(deployment.deployment_id);
    }
  }, [isActive, hasAnyRun, deployment.deployment_id]);

  function handleRunFirst() {
    trackRunCtaClicked("post_deploy_hero", deployment.deployment_id);
    onRunFirst();
  }

  return (
    <GlassCard className="overflow-hidden border-emerald-500/25 bg-gradient-to-br from-emerald-500/10 via-emerald-950/20 to-transparent shadow-sm shadow-emerald-500/5">
      <div className="space-y-5 p-6 sm:p-8">
        <SuccessBanner message={SUCCESS_MESSAGES.deployActive} />

        {isActive && !hasAnyRun && !running ? (
          <div className="rounded-lg border border-primary/25 bg-primary/5 px-4 py-3">
            <p className="text-sm font-medium text-foreground">Next step</p>
            <p className="mt-1 text-sm text-neutral-400">{ACTIVATION_COPY.deployNextStep}</p>
          </div>
        ) : null}

        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-xl">
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-400/90">
              Your agent is live
            </p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">
              {deployment.agent_name}{" "}
              <span className="font-normal text-neutral-500">v{deployment.version}</span>
            </h2>
            <p className="mt-2 text-sm text-neutral-400">
              {isActive
                ? hasAnyRun
                  ? "Open a recent run below or queue another task."
                  : "Deploy is done — run a task next to see live logs."
                : `${deploymentStatusLabel(deployment.status)} — you can run tasks once status is ready.`}
            </p>
          </div>

          {isActive && !running ? (
            <Button
              type="button"
              size="lg"
              className="h-12 shrink-0 px-8 text-base shadow-lg shadow-primary/25"
              onClick={handleRunFirst}
            >
              <PlayCircle className="mr-2 h-5 w-5" />
              {hasAnyRun ? NEXT_STEP.runAgain : NEXT_STEP.runFirst}
            </Button>
          ) : null}
        </div>

        {running ? <ExecutionStarting /> : null}

        {hasAnyRun ? (
          <div className="flex flex-wrap gap-3 text-sm">
            <Link
              href="/runs"
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-neutral-300 transition-colors hover:bg-white/10 hover:text-foreground"
            >
              {NEXT_STEP.viewRuns}
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            {hasCompletedRun ? (
              <Link
                href="/api-keys"
                className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-neutral-500 transition-colors hover:text-primary"
              >
                <KeyRound className="mr-1.5 h-3.5 w-3.5" />
                {NEXT_STEP.createKey}
              </Link>
            ) : null}
          </div>
        ) : null}

        {recentTasks.length > 0 ? (
          <div className="border-t border-white/5 pt-4">
            <p className="text-xs font-medium text-neutral-500">Recent runs</p>
            <ul className="mt-2 divide-y divide-white/5">
              {recentTasks.slice(0, 3).map((t) => (
                <li key={t.task_id}>
                  <Link
                    href={taskTraceHref(t.task_id, projectId)}
                    className="flex items-center justify-between py-2.5 text-sm transition-colors hover:text-primary"
                  >
                    <span className="text-foreground">
                      {t.agent_name || deployment.agent_name || "Task"}
                    </span>
                    <span className="capitalize text-neutral-500">{t.status ?? "—"}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ) : isActive && !running ? (
          <p className="border-t border-white/5 pt-4 text-sm text-neutral-500">
            No runs yet — use the button above. You&apos;ll jump straight to the live trace.
          </p>
        ) : null}

        {isActive && hasCompletedRun ? (
          <div className="border-t border-white/5 pt-4">
            <FeedbackPrompt context="post_deploy_success" title="How was deploy + first run?" />
          </div>
        ) : null}
      </div>
    </GlassCard>
  );
}

