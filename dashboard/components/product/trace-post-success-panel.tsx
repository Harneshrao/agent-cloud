"use client";

import Link from "next/link";
import { ArrowRight, KeyRound, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/product/glass-card";
import { ACTIVATION_COPY, NEXT_STEP } from "@/lib/trust-copy";
import { trackRunAgainClicked, trackSecondTaskStarted } from "@/lib/analytics";
import { hasOnboardingStep } from "@/lib/onboarding";

export function TracePostSuccessPanel({
  taskId,
  deploymentId,
  running,
  onRunAgain,
}: {
  taskId: string;
  deploymentId: string;
  running: boolean;
  onRunAgain: () => void;
}) {
  function handleRunAgain() {
    trackRunAgainClicked(taskId, deploymentId);
    if (hasOnboardingStep("viewed_logs")) {
      trackSecondTaskStarted(deploymentId);
    }
    onRunAgain();
  }

  return (
    <GlassCard className="border-primary/20 bg-primary/5 p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-primary">What&apos;s next</p>
      <p className="mt-1 text-sm text-neutral-300">{ACTIVATION_COPY.traceSuccessNext}</p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Button type="button" size="lg" disabled={running} onClick={handleRunAgain}>
          <PlayCircle className="mr-2 h-4 w-4" />
          {running ? "Starting…" : NEXT_STEP.runAgain}
        </Button>
        <Link
          href="/api-keys"
          className="inline-flex h-11 items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-5 text-sm font-medium text-neutral-200 transition-colors hover:bg-white/10"
        >
          <KeyRound className="h-4 w-4" />
          {NEXT_STEP.createKey}
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
      <p className="mt-3 text-xs text-neutral-500">{ACTIVATION_COPY.apiKeyContext}</p>
    </GlassCard>
  );
}
