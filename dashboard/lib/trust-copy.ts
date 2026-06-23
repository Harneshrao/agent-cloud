/**
 * Trust-centered product copy — developer mental models, not infra jargon.
 */

export function deploymentStatusLabel(status: string): string {
  const s = status.toLowerCase();
  const map: Record<string, string> = {
    active: "Live · ready to run",
    failed: "Needs attention",
    deploying: "Starting up",
    superseded: "Superseded by a newer version",
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

/** Resolve display status when DB still has legacy rolled_back from promotion. */
export function deploymentEffectiveStatus(
  deployment: {
    status: string;
    deployment_id: string;
    agent_name: string;
    previous_deployment_id?: string | null;
    activated_at?: string | null;
    updated_at?: string;
  },
  allDeployments: Array<{
    deployment_id: string;
    agent_name: string;
    status: string;
    activated_at?: string | null;
    updated_at?: string;
  }>
): string {
  const raw = deployment.status.toLowerCase();
  if (raw !== "rolled_back") return raw;

  const ts = deployment.activated_at ?? deployment.updated_at ?? "";
  const priorRestored = deployment.previous_deployment_id
    ? allDeployments.some(
        (d) =>
          d.deployment_id === deployment.previous_deployment_id && d.status === "active"
      )
    : false;
  if (priorRestored) return "rolled_back";

  const supersededByChild = allDeployments.some(
    (d) =>
      d.deployment_id !== deployment.deployment_id &&
      d.previous_deployment_id === deployment.deployment_id
  );
  if (supersededByChild) return "superseded";

  const newerActive = allDeployments.some(
    (d) =>
      d.deployment_id !== deployment.deployment_id &&
      d.agent_name === deployment.agent_name &&
      d.status === "active" &&
      (d.activated_at ?? d.updated_at ?? "") > ts
  );
  if (newerActive) return "superseded";

  return "rolled_back";
}

export function deploymentDisplayLabel(
  deployment: Parameters<typeof deploymentEffectiveStatus>[0],
  allDeployments: Parameters<typeof deploymentEffectiveStatus>[1]
): string {
  return deploymentStatusLabel(deploymentEffectiveStatus(deployment, allDeployments));
}

export function deploymentStatusTone(
  status: string
): "ready" | "pending" | "attention" {
  const s = status.toLowerCase();
  if (s === "active") return "ready";
  if (s === "failed" || s === "rolled_back") return "attention";
  if (s === "superseded") return "pending";
  return "pending";
}

export function deploymentDisplayTone(
  deployment: Parameters<typeof deploymentEffectiveStatus>[0],
  allDeployments: Parameters<typeof deploymentEffectiveStatus>[1]
): ReturnType<typeof deploymentStatusTone> {
  return deploymentStatusTone(deploymentEffectiveStatus(deployment, allDeployments));
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
