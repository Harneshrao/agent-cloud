/**
 * Product analytics — lightweight activation & PMF event tracking.
 */

import { API_BASE } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import { getActiveProjectId } from "@/lib/project";

const SESSION_KEY = "agent_cloud_session_id";

export type ProductEventPayload = {
  event_name: string;
  project_id?: string;
  deployment_id?: string;
  task_id?: string;
  session_id?: string;
  onboarding_step?: string;
  properties?: Record<string, unknown>;
};

export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `sess_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

/** Fire-and-forget product event (never blocks UX). */
export function trackProductEvent(
  eventName: string,
  props?: {
    onboarding_step?: string;
    deployment_id?: string;
    task_id?: string;
    properties?: Record<string, unknown>;
  }
): void {
  if (typeof window === "undefined") return;
  const token = getAccessToken();
  const projectId = getActiveProjectId();
  const body = {
    events: [
      {
        event_name: eventName,
        project_id: projectId || undefined,
        deployment_id: props?.deployment_id,
        task_id: props?.task_id,
        session_id: getSessionId(),
        onboarding_step: props?.onboarding_step,
        properties: props?.properties ?? {},
      },
    ],
  };
  fetch(`${API_BASE}/analytics/events`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(projectId ? { "X-Project-ID": projectId } : {}),
    },
    body: JSON.stringify(body),
    keepalive: true,
  }).catch(() => {});
}

export function trackPageView(path: string): void {
  trackProductEvent("page_viewed", { properties: { path } });
}

export function trackRunCtaClicked(source: string, deploymentId?: string): void {
  trackProductEvent("run_cta_clicked", {
    deployment_id: deploymentId,
    properties: { source },
  });
}

export function trackRunAgainClicked(taskId: string, deploymentId?: string): void {
  trackProductEvent("run_again_clicked", {
    task_id: taskId,
    deployment_id: deploymentId,
    properties: { is_repeat: true },
  });
}

export function trackSecondTaskStarted(deploymentId: string): void {
  trackProductEvent("second_task_started", { deployment_id: deploymentId });
}

export function trackDeployWithoutRunView(deploymentId: string): void {
  trackProductEvent("deploy_without_run_view", { deployment_id: deploymentId });
}

export function submitProductFeedback(
  rating: number,
  comment: string,
  context: string
): void {
  trackProductEvent("feedback_submitted", {
    properties: { rating, comment: comment.slice(0, 2000), context },
  });
}

export function submitUserResearchSession(props: {
  clarity_rating: number;
  would_use_again: number;
  needed_help: boolean;
  comment?: string;
}): void {
  trackProductEvent("user_research_session_completed", {
    properties: {
      clarity_rating: props.clarity_rating,
      would_use_again: props.would_use_again,
      needed_help: props.needed_help,
      comment: (props.comment ?? "").slice(0, 2000),
      cohort: "first_5",
    },
  });
}

export interface PmfSummary {
  funnel: {
    window_days: number;
    steps: Array<{
      event: string;
      unique_users: number;
      unique_sessions: number;
      count: number;
      drop_off_pct_from_previous: number | null;
    }>;
    activation_rate_pct: number;
    median_time_to_activation_seconds: number | null;
    activated_users: number;
    signup_users: number;
  };
  deployment: Record<string, unknown>;
  trust: Record<string, unknown>;
  pmf_health: { score: number; label: string };
  ops_alerts?: Array<{
    severity: string;
    code: string;
    message: string;
  }>;
  targets?: Record<string, number>;
  recent_feedback: Array<{
    event_id: string;
    properties: Record<string, unknown>;
    created_at: string;
  }>;
  user_research_cohort?: Array<{
    user_id: string;
    first_seen: string | null;
    time_to_activation_seconds: number | null;
    steps: Record<string, boolean>;
    would_use_again?: number;
    needed_help?: boolean;
    clarity_rating?: number;
  }>;
  activation_gaps?: {
    window_days: number;
    deploy_without_run_users: number;
    run_without_trace_users: number;
    trace_without_key_users: number;
    deploy_without_run_views: number;
    run_cta_clicks: number;
    second_task_starts: number;
    run_again_clicks: number;
    repeat_intent_users: number;
    repeat_rate_pct: number | null;
    page_views: number;
  };
  signals: Record<string, string[]>;
}
