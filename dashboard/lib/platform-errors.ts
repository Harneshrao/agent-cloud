/**
 * Canonical error classification — calm, trust-preserving UX.
 */

import { isApiRequestError } from "@/lib/api-errors";
import { isProjectContextError, NO_PROJECT_MESSAGE } from "@/lib/project-messages";

const OFFLINE_MARKERS = [
  "not reachable",
  "failed to fetch",
  "load failed",
  "can't connect",
  "api unavailable",
  "reconnecting",
];

export type PlatformErrorKind =
  | "degraded"
  | "auth"
  | "quota"
  | "project"
  | "not_found"
  | "validation"
  | "server"
  | "unknown";

export type PlatformFault = "user" | "platform" | "unknown";

export type PlatformTone = "calm" | "attention" | "critical";

export interface PlatformErrorView {
  kind: PlatformErrorKind;
  tone: PlatformTone;
  title: string;
  message: string;
  hint?: string;
  diagnostic?: string;
  fault: PlatformFault;
  retryable: boolean;
  dataSafe: boolean;
}

function isOfflineMessage(message: string): boolean {
  const m = message.toLowerCase();
  return OFFLINE_MARKERS.some((marker) => m.includes(marker)) || m.includes("network");
}

function devDiagnostic(): string | undefined {
  if (process.env.NEXT_PUBLIC_DEV_HINTS === "1") {
    return "Developer check: API should be at http://127.0.0.1:8000 (not port 3000). Start stack with py -3.11 run_all.py";
  }
  return undefined;
}

/** Map any thrown value into a product-ready, calm error view. */
export function toPlatformError(
  input: unknown,
  fallback = "Something went wrong"
): PlatformErrorView {
  const statusCode = isApiRequestError(input) ? input.statusCode : undefined;
  const raw = isApiRequestError(input)
    ? input.message
    : input instanceof Error
      ? input.message
      : typeof input === "string"
        ? input
        : fallback;

  if (isOfflineMessage(raw) || statusCode === 0) {
    return {
      kind: "degraded",
      tone: "calm",
      title: "Live sync paused",
      message:
        "Some live platform features are reconnecting. Your deployments and execution history are preserved.",
      hint: undefined,
      diagnostic: devDiagnostic(),
      fault: "platform",
      retryable: true,
      dataSafe: true,
    };
  }

  if (
    raw.toLowerCase().includes("session") ||
    raw.toLowerCase().includes("unauthorized") ||
    statusCode === 401 ||
    statusCode === 403
  ) {
    const forbidden = statusCode === 403 || raw.toLowerCase().includes("access denied");
    return {
      kind: "auth",
      tone: "attention",
      title: forbidden ? "Access needed" : "Sign in again",
      message: forbidden
        ? "You don't have access to this project. Switch projects or ask the owner for access."
        : "Your session ended. Sign in again to continue — nothing was deleted.",
      fault: "user",
      retryable: false,
      dataSafe: true,
    };
  }

  if (
    raw.toLowerCase().includes("quota") ||
    raw.toLowerCase().includes("rate limit") ||
    statusCode === 429
  ) {
    return {
      kind: "quota",
      tone: "attention",
      title: "Usage limit reached",
      message: "You've hit a plan limit for this window. Your existing data is safe.",
      hint: "Open Limits to see usage, or wait for the window to reset.",
      fault: "user",
      retryable: false,
      dataSafe: true,
    };
  }

  if (isProjectContextError(raw) || raw === NO_PROJECT_MESSAGE) {
    return {
      kind: "project",
      tone: "attention",
      title: "Choose a project",
      message: NO_PROJECT_MESSAGE,
      hint: "Create or select a project in the top bar — we'll send context automatically.",
      fault: "user",
      retryable: false,
      dataSafe: true,
    };
  }

  if (statusCode === 404 || raw.toLowerCase().includes("not found")) {
    return {
      kind: "not_found",
      tone: "attention",
      title: "Couldn't load this view",
      message:
        "We couldn't find deployments for this project. Switch projects or deploy again — your account is fine.",
      hint: "Try Projects → select the right workspace, then return here.",
      diagnostic: devDiagnostic(),
      fault: "platform",
      retryable: true,
      dataSafe: true,
    };
  }

  const lower = raw.toLowerCase();
  if (lower.includes("validation") || lower.includes("invalid")) {
    return {
      kind: "validation",
      tone: "attention",
      title: "Check your agent package",
      message: raw.length < 280 ? raw : "The package didn't pass validation. Fix agent.yaml and agent.py, then upload again.",
      hint: "Use the sample echo agent to confirm the platform works, then retry your ZIP.",
      fault: "user",
      retryable: false,
      dataSafe: true,
    };
  }

  if (statusCode && statusCode >= 500) {
    return {
      kind: "server",
      tone: "attention",
      title: "Temporary platform issue",
      message: "Something failed on our side. Your deployments and tasks are safe — retry in a moment.",
      diagnostic: raw.length < 200 ? raw : undefined,
      fault: "platform",
      retryable: true,
      dataSafe: true,
    };
  }

  return {
    kind: "unknown",
    tone: "attention",
    title: "Something didn't work",
    message: raw.length < 280 ? raw : "An unexpected error occurred. Retry, or contact support with the page name.",
    hint: "If this persists, note what you clicked and we'll help.",
    fault: "unknown",
    retryable: true,
    dataSafe: true,
  };
}
