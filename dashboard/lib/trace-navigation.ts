import { getActiveProjectId } from "@/lib/project";

/** Task trace URL with optional project hint for API context. */
export function taskTraceHref(taskId: string, projectId?: string): string {
  const pid = (projectId || getActiveProjectId()).trim();
  const base = `/tasks/${taskId}`;
  if (!pid) return base;
  return `${base}?project=${encodeURIComponent(pid)}`;
}

export function readProjectIdFromSearch(
  params: URLSearchParams | null | undefined
): string {
  if (!params) return "";
  return (params.get("project") || params.get("projectId") || "").trim();
}
