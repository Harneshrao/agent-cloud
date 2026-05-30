/**
 * First-success loop progress (localStorage + reactive updates).
 */

const PREFIX = "agent_cloud_onboarding_";
export const ONBOARDING_CHANGED_EVENT = "agentcloud:onboarding-changed";

export type OnboardingStepId =
  | "project"
  | "deployed"
  | "ran"
  | "viewed_logs"
  | "api_key";

function notifyOnboardingChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(ONBOARDING_CHANGED_EVENT));
}

export function markOnboardingStep(step: OnboardingStepId): void {
  if (typeof window === "undefined") return;
  const key = `${PREFIX}${step}`;
  if (localStorage.getItem(key) === "1") return;
  localStorage.setItem(key, "1");
  notifyOnboardingChanged();
  import("@/lib/analytics")
    .then(({ trackProductEvent }) => {
      trackProductEvent("onboarding_step", { onboarding_step: step });
    })
    .catch(() => {});
}

export function hasOnboardingStep(step: OnboardingStepId): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(`${PREFIX}${step}`) === "1";
}

export function getOnboardingProgress(): Record<OnboardingStepId, boolean> {
  return {
    project: hasOnboardingStep("project"),
    deployed: hasOnboardingStep("deployed"),
    ran: hasOnboardingStep("ran"),
    viewed_logs: hasOnboardingStep("viewed_logs"),
    api_key: hasOnboardingStep("api_key"),
  };
}
