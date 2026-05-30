/**
 * Trust-centered product copy — developer mental models, not infra jargon.
 */

export function deploymentStatusLabel(status: string): string {
  const s = status.toLowerCase();
  const map: Record<string, string> = {
    active: "Ready to run",
    failed: "Needs attention",
    deploying: "Starting up",
    rolled_back: "Previous version restored",
    archived: "Archived",
    uploaded: "Uploaded",
    validating: "Checking package",
    validated: "Validated",
    building: "Building",
    ready: "Ready to activate",
  };
  return map[s] ?? status.replace(/_/g, " ");
}

export function deploymentStatusTone(
  status: string
): "ready" | "pending" | "attention" {
  const s = status.toLowerCase();
  if (s === "active") return "ready";
  if (s === "failed" || s === "rolled_back") return "attention";
  return "pending";
}

export const SUCCESS_MESSAGES = {
  deployActive: "Your agent is live — ready to execute tasks.",
  taskQueued: "Task queued — opening live trace.",
  taskStarting: "Starting execution — workers will pick this up momentarily.",
  retryOk: "Execution recovered successfully.",
  logsStreaming: "Logs streaming normally.",
  rollbackOk: "Deployment restored to the previous version.",
} as const;

export const NEXT_STEP = {
  runFirst: "Run your first task",
  viewRuns: "Runs & traces",
  viewLogs: "Runs & traces",
  createKey: "Create API key",
  runAgain: "Run again",
} as const;

export const ACTIVATION_COPY = {
  deployNextStep:
    "Step 2 of 4: Run a task to see live logs. Most first runs finish in under a minute.",
  traceSuccessNext:
    "Your agent ran successfully. Run again to confirm repeatability, then create an API key.",
  apiKeyContext: "Use an API key to run this deployment from your app, CI, or scripts.",
  runsNavHint: "Every execution and its logs live here.",
} as const;

/** Calm degraded-mode copy — never competes with success state. */
export const DEGRADED_CONNECTIVITY = {
  /** Single-line footnote (deployments page, below success). */
  footnote:
    "Some live platform features are reconnecting. Your deployment is safe — run tasks anytime.",
  /** Ultra-short global strip (non-deployments routes). */
  strip: "Some live features are reconnecting.",
} as const;
