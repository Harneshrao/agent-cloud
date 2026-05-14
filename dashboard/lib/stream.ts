import { getApiBase } from "@/lib/auth";

export function getSystemStreamUrl(): string {
  const base = getApiBase().replace(/^http/, "http");
  return `${base}/system/stream`;
}

export function getWorkflowLogStreamUrl(taskId: number): string {
  const base = getApiBase().replace(/^http/, "http");
  return `${base}/workflows/${taskId}/logs/stream`;
}

export interface MetricsUpdateEvent {
  type: "metrics_update";
  data: {
    queue_length?: number;
    workers_active?: number;
    containers_idle?: number;
    containers_busy?: number;
    tasks_running?: number;
    tasks_failed_last_hour?: number;
  };
}

export type SystemStreamEvent = MetricsUpdateEvent;
