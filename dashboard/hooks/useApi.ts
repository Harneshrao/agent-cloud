"use client";

import useSWR from "swr";

export function useApi<T = unknown>(path: string) {
  const { data, error, isLoading } = useSWR<T>(path);

  return {
    data,
    loading: isLoading,
    error: error ? "Backend error" : null,
  };
}

