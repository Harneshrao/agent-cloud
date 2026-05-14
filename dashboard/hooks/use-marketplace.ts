"use client";

import useSWR from "swr";
import type { MarketplaceAgent } from "@/types";

export type MarketplaceFilters = {
  category?: string;
  sort?: string;
  min_rating?: number;
  max_price?: number;
  q?: string;
};

export function useMarketplace(filters?: MarketplaceFilters) {
  const sp = new URLSearchParams();
  if (filters?.category) sp.set("category", filters.category);
  if (filters?.sort) sp.set("sort", filters.sort);
  if (filters?.min_rating != null) sp.set("min_rating", String(filters.min_rating));
  if (filters?.max_price != null) sp.set("max_price", String(filters.max_price));
  const q = sp.toString();
  const key = `/marketplace/agents${q ? `?${q}` : ""}`;

  const { data, error, isLoading, mutate } = useSWR<{ agents: MarketplaceAgent[] }>(key);

  let agents = data?.agents ?? [];
  if (filters?.q?.trim()) {
    const needle = filters.q.toLowerCase();
    agents = agents.filter(
      (a) =>
        a.agent_name.toLowerCase().includes(needle) ||
        (a.description || "").toLowerCase().includes(needle) ||
        (a.developer || "").toLowerCase().includes(needle)
    );
  }

  return {
    agents,
    loading: isLoading,
    error: error instanceof Error ? error : error ? new Error("Failed to load marketplace") : null,
    refetch: () => mutate(),
  };
}
