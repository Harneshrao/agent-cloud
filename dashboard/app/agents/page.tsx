"use client";

import { useEffect, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { AgentCard } from "@/components/agent-card";
import { fetchAgentsStore } from "@/lib/api";
import type { AgentStoreItem } from "@/types";
import { Bot } from "lucide-react";

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentStoreItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await fetchAgentsStore();
        if (!cancelled) setAgents(data.agents ?? []);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load agents");
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Agent Marketplace</h1>
        <p className="text-neutral-400 mt-1">Discover and run published agents</p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {agents === null ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[220px] rounded-2xl" />
          ))}
        </div>
      ) : agents.length === 0 ? (
        <EmptyState
          icon={<Bot className="h-12 w-12" />}
          title="No agents yet"
          description="Publish agents via the API or CLI to see them here. Then run them with a task prompt from this page."
        />
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard key={`${agent.name}-${agent.version}`} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}
