"use client";

import { useEffect, useState } from "react";
import {
  ONBOARDING_CHANGED_EVENT,
  getOnboardingProgress,
  type OnboardingStepId,
} from "@/lib/onboarding";

/** Reactive onboarding progress (updates when markOnboardingStep runs). */
export function useOnboardingProgress(): Record<OnboardingStepId, boolean> {
  const [progress, setProgress] = useState(getOnboardingProgress);

  useEffect(() => {
    const refresh = () => setProgress(getOnboardingProgress());
    refresh();
    window.addEventListener(ONBOARDING_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(ONBOARDING_CHANGED_EVENT, refresh);
  }, []);

  return progress;
}
