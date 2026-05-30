"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Bot,
  Star,
  User,
  DollarSign,
  ArrowLeft,
  Loader2,
  Play,
  FileJson,
  BookOpen,
  History,
} from "lucide-react";
import { fetchMarketplaceAgents, installAgent } from "@/lib/api";
import type { MarketplaceAgent } from "@/types";
import { PremiumCard } from "@/components/ui/premium-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "Overview", icon: BookOpen },
  { id: "inputs", label: "Inputs", icon: FileJson },
  { id: "outputs", label: "Outputs", icon: FileJson },
  { id: "pricing", label: "Pricing", icon: DollarSign },
  { id: "history", label: "Run history", icon: History },
] as const;

export default function AgentDetailPage({
  params,
}: {
  params: Promise<{ agentName?: string }>;
}) {
  const router = useRouter();
  const resolved = React.use(params);
  const agentName = decodeURIComponent((resolved.agentName as string) || "");
  const [agent, setAgent] = useState<MarketplaceAgent | null>(null);
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState(false);
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("overview");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetchMarketplaceAgents({});
        const found = res.agents.find(
          (a) => a.agent_name.toLowerCase() === agentName.toLowerCase()
        );
        if (!cancelled) setAgent(found ?? null);
      } catch {
        if (!cancelled) setAgent(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
  }, [agentName]);

  const handleInstall = async () => {
    if (!agent) return;
    setInstalling(true);
    try {
      await installAgent(agent.agent_name);
      router.push("/");
    } finally {
      setInstalling(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-9 w-48 bg-elevated" />
        <Skeleton className="h-64 rounded-xl bg-card" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="space-y-6">
        <Link
          href="/marketplace"
          className="inline-flex items-center gap-2 text-body text-foreground-secondary hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Back to marketplace
        </Link>
        <p className="text-body text-muted">Agent not found.</p>
      </div>
    );
  }

  const hasInputSchema =
    agent.input_schema && Object.keys(agent.input_schema).length > 0;

  return (
    <div className="space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between"
      >
        <div className="flex items-start gap-6">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-primary-soft text-primary">
            <Bot className="h-8 w-8" />
          </div>
          <div>
            <Link
              href="/marketplace"
              className="inline-flex items-center gap-2 text-body text-foreground-secondary hover:text-foreground mb-2"
            >
              <ArrowLeft className="h-4 w-4" /> Marketplace
            </Link>
            <h1 className="text-page-title text-foreground tracking-tight">
              {agent.agent_name}
            </h1>
            <p className="mt-2 text-body text-foreground-secondary max-w-2xl">
              {agent.description || "No description."}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button asChild size="lg" variant="secondary" className="gap-2">
            <Link href="/">
              <Play className="h-4 w-4" />
              Run agent
            </Link>
          </Button>
          <Button size="lg" onClick={handleInstall} disabled={installing} className="gap-2">
            {installing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Installing…
              </>
            ) : (
              "Install agent"
            )}
          </Button>
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "flex items-center gap-2 rounded-t-lg px-4 py-3 text-body font-medium transition-colors",
                tab === t.id
                  ? "bg-card text-primary border border-border border-b-0 -mb-px"
                  : "text-foreground-secondary hover:text-foreground"
              )}
            >
              <t.icon className="h-4 w-4" />
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {tab === "overview" && (
            <>
              {agent.example_output != null && (
                <PremiumCard>
                  <h2 className="text-section-title text-foreground">
                    Example output
                  </h2>
                  <pre className="mt-4 rounded-lg border border-border bg-background p-4 text-body text-foreground-secondary overflow-x-auto font-mono">
                    {JSON.stringify(agent.example_output, null, 2)}
                  </pre>
                </PremiumCard>
              )}
              {agent.capabilities?.length > 0 && (
                <PremiumCard>
                  <h2 className="text-section-title text-foreground">
                    Capabilities
                  </h2>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {agent.capabilities.map((c) => (
                      <span
                        key={c}
                        className="rounded-lg bg-elevated px-3 py-1 text-label text-foreground-secondary"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </PremiumCard>
              )}
            </>
          )}
          {tab === "inputs" && (
            <PremiumCard>
              <h2 className="text-section-title text-foreground">
                Input parameters
              </h2>
              <p className="mt-0.5 text-body text-foreground-secondary">
                Configure these after installing.
              </p>
              {hasInputSchema ? (
                <ul className="mt-6 space-y-3">
                  {Object.entries(agent.input_schema!).map(([key, spec]) => (
                    <li
                      key={key}
                      className="flex justify-between rounded-lg border border-border bg-elevated/30 px-4 py-3 text-body"
                    >
                      <span className="text-foreground">{key}</span>
                      <span className="text-muted">
                        {(spec as { type?: string }).type ?? "string"}
                        {(spec as { required?: boolean }).required &&
                          " · required"}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-6 text-body text-muted">
                  No input schema defined.
                </p>
              )}
            </PremiumCard>
          )}
          {tab === "outputs" && (
            <PremiumCard>
              <h2 className="text-section-title text-foreground">
                Output schema
              </h2>
              <p className="mt-0.5 text-body text-foreground-secondary">
                Structure returned by this agent.
              </p>
              {agent.example_output != null ? (
                <pre className="mt-6 rounded-lg border border-border bg-background p-4 text-body text-foreground-secondary overflow-x-auto font-mono">
                  {JSON.stringify(agent.example_output, null, 2)}
                </pre>
              ) : (
                <p className="mt-6 text-body text-muted">
                  No example output available.
                </p>
              )}
            </PremiumCard>
          )}
          {tab === "pricing" && (
            <PremiumCard>
              <h2 className="text-section-title text-foreground">
                Pricing model
              </h2>
              <p className="mt-2 text-body text-foreground-secondary">
                {agent.price_per_run === 0
                  ? "Free"
                  : `$${agent.price_per_run.toFixed(2)} per run`}{" "}
                {agent.currency && `(${agent.currency})`}
              </p>
            </PremiumCard>
          )}
          {tab === "history" && (
            <PremiumCard>
              <h2 className="text-section-title text-foreground">
                Run history
              </h2>
              <p className="mt-0.5 text-body text-foreground-secondary">
                Past runs for this agent (after installation).
              </p>
              <p className="mt-6 text-body text-muted">
                Install the agent to run it and see history on the dashboard.
              </p>
              <Button asChild variant="secondary" className="mt-4">
                <Link href="/">Go to dashboard</Link>
              </Button>
            </PremiumCard>
          )}
        </div>

        <div className="space-y-6">
          <PremiumCard>
            <h2 className="text-label text-muted uppercase tracking-wider">
              Developer
            </h2>
            <p className="mt-2 flex items-center gap-2 text-body text-foreground">
              <User className="h-4 w-4 text-muted" />
              {agent.developer || "—"}
            </p>
          </PremiumCard>
          <PremiumCard>
            <h2 className="text-label text-muted uppercase tracking-wider">
              Pricing
            </h2>
            <p className="mt-2 flex items-center gap-2 text-body text-foreground">
              <DollarSign className="h-4 w-4 text-muted" />
              {agent.price_per_run === 0
                ? "Free"
                : `$${agent.price_per_run.toFixed(2)} per run`}
            </p>
            {agent.currency && (
              <p className="mt-1 text-label text-muted">{agent.currency}</p>
            )}
          </PremiumCard>
          {agent.rating != null && (
            <PremiumCard>
              <h2 className="text-label text-muted uppercase tracking-wider">
                Rating
              </h2>
              <p className="mt-2 flex items-center gap-2 text-body text-foreground">
                <Star className="h-4 w-4 fill-warning text-warning" />
                {agent.rating}
              </p>
            </PremiumCard>
          )}
        </div>
      </div>
    </div>
  );
}
