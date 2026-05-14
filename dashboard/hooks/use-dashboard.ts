"use client";

import useSWR from "swr";
import type { DashboardData } from "@/types";

const defaultDashboardData: DashboardData = {
  project_id: 0,
  installations: [],
  recent_runs: [],
  runs_today: 0,
  cost_today: 0,
  monthly_usage: { runs_this_month: 0, execution_time_this_month_ms: 0 },
  total_runs: 0,
  total_agent_cost: 0,
  runs_per_agent: [],
};

export function useDashboard() {
  const { data, error, isLoading, mutate } = useSWR<DashboardData>("/dashboard");

  return {
    data: data ?? defaultDashboardData,
    loading: isLoading,
    error: error instanceof Error ? error : error ? new Error("Failed to load dashboard") : null,
    refetch: () => mutate(),
  };
}
