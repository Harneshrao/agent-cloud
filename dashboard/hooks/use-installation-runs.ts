"use client";

import useSWR from "swr";
import type { AgentRun } from "@/types";

export function useInstallationRuns(installationId: number | null, limit = 50) {
  const key =
    installationId == null
      ? null
      : `/agents/installations/${installationId}/runs?limit=${limit}&offset=0`;

  const { data, error, isLoading, mutate } = useSWR<{ runs: AgentRun[] }>(key);

  return {
    runs: data?.runs ?? [],
    loading: isLoading,
    error: error instanceof Error ? error : error ? new Error("Failed to load runs") : null,
    refetch: () => mutate(),
  };
}
