"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Bot, Star, DollarSign, User, BadgeCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { MarketplaceAgent } from "@/types";

const CATEGORIES = [
  "Marketing",
  "Sales",
  "Research",
  "Productivity",
  "Finance",
  "Developer Tools",
] as const;

function getCategoryTag(capabilities: string[] = []) {
  const cap = capabilities[0]?.toLowerCase() ?? "";
  const found = CATEGORIES.find((c) => cap.includes(c.toLowerCase()));
  return found ?? (capabilities[0] || "General");
}

interface AgentMarketplaceCardProps {
  agent: MarketplaceAgent;
  onInstall?: (agentName: string) => void;
  installing?: string | null;
}

export function AgentMarketplaceCard({
  agent,
  onInstall,
  installing = null,
}: AgentMarketplaceCardProps) {
  const category = getCategoryTag(agent.capabilities);
  const price = agent.price_per_run ?? 0;
  const currency = agent.currency ?? "USD";

  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ duration: 0.2 }}
      className="group rounded-xl border border-border bg-card p-6 transition-all duration-200 hover:border-primary/30 hover:bg-elevated/80 hover:shadow-glow card-hover-lift"
    >
      <Link href={`/marketplace/${encodeURIComponent(agent.agent_name)}`} className="block">
        <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
              <Bot className="h-6 w-6" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-section-title text-foreground truncate">
                {agent.agent_name}
              </h3>
              <p className="mt-1 text-body text-foreground-secondary line-clamp-2">
                {agent.description || "No description."}
              </p>
              {agent.developer && (
                <p className="mt-1.5 flex items-center gap-1.5 text-label text-muted">
                  <User className="h-3.5 w-3.5" />
                  {agent.developer}
                  {agent.developer_verified && (
                    <BadgeCheck className="h-3.5 w-3.5 text-primary" aria-label="Verified developer" />
                  )}
                </p>
              )}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-elevated px-2 py-0.5 text-label text-muted">
                  {category}
                </span>
                {agent.rating != null && (
                  <span className="flex items-center gap-1 text-label text-foreground-secondary">
                    <Star className="h-3.5 w-3.5 fill-warning text-warning" />
                    {agent.rating.toFixed(1)}
                  </span>
                )}
                {(agent.install_count ?? 0) > 0 && (
                  <span className="text-label text-muted">
                    {(agent.install_count ?? 0).toLocaleString()} installs
                  </span>
                )}
                <span className="flex items-center gap-1 text-label text-foreground-secondary">
                  <DollarSign className="h-3.5 w-3.5" />
                  {price.toFixed(2)}/{currency} per run
                </span>
              </div>
            </div>
          </div>
      </Link>
      {onInstall && (
        <div className="mt-4 flex justify-end" onClick={(e) => e.preventDefault()}>
          <Button
            size="sm"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onInstall(agent.agent_name);
            }}
            disabled={installing === agent.agent_name}
          >
            {installing === agent.agent_name ? "Installing…" : "Install"}
          </Button>
        </div>
      )}
    </motion.div>
  );
}
