/**
 * Active project context for X-Project-ID header.
 */

const PROJECT_KEY = "agent_cloud_project_id";

/** Active project UUID from localStorage (set by ActiveProjectProvider / topbar). */
export function getActiveProjectId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(PROJECT_KEY) || "";
}

/** Resolve project for API calls: explicit > localStorage. */
export function resolveActiveProjectId(explicit?: string | null): string {
  const fromArg = (explicit ?? "").trim();
  if (fromArg) return fromArg;
  return getActiveProjectId().trim();
}

export function setActiveProjectId(projectId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(PROJECT_KEY, projectId);
}

export function clearActiveProjectId(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(PROJECT_KEY);
}
