"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Search } from "lucide-react";
import { useMarketplace } from "@/hooks/use-marketplace";
import { AgentMarketplaceCard } from "@/components/marketplace/agent-marketplace-card";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Bot } from "lucide-react";
import { installAgent } from "@/lib/api";
import { useRouter } from "next/navigation";

const CATEGORIES = [
  "Marketing",
  "Sales",
  "Research",
  "Productivity",
  "Finance",
  "Developer Tools",
];

const SORT_OPTIONS = [
  { value: "", label: "Default" },
  { value: "popularity", label: "Popularity" },
  { value: "rating", label: "Rating" },
  { value: "price_asc", label: "Price ↑" },
  { value: "price_desc", label: "Price ↓" },
];

export default function MarketplacePage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string | undefined>();
  const [sort, setSort] = useState<string | undefined>();
  const [installing, setInstalling] = useState<string | null>(null);

  const { agents, loading, error, refetch } = useMarketplace({
    category,
    sort: sort || undefined,
    q: search.trim() || undefined,
  });

  const handleInstall = async (agentName: string) => {
    setInstalling(agentName);
    try {
      await installAgent(agentName);
      router.push("/");
    } finally {
      setInstalling(null);
    }
  };

  return (
    <div className="space-y-8">
      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 flex items-center justify-between gap-4 flex-wrap">
          <span>Couldn’t load marketplace. Showing cached or empty list.</span>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-page-title text-foreground tracking-tight">
          Marketplace
        </h1>
        <p className="mt-2 text-body text-foreground-secondary">
          Discover and install AI agents. Configure once, run anytime.
        </p>
      </motion.div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            placeholder="Search agents…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 rounded-xl bg-card border-border text-foreground placeholder:text-muted"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-label text-muted mr-1">Sort:</span>
          {SORT_OPTIONS.map((o) => (
            <button
              key={o.label}
              onClick={() => setSort(o.value || undefined)}
              className={`rounded-lg px-3 py-1.5 text-label font-medium transition-colors ${
                (sort || "") === o.value
                  ? "bg-primary-soft text-primary"
                  : "bg-elevated text-foreground-secondary hover:text-foreground"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="text-label text-muted mr-1">Category:</span>
        <button
          onClick={() => setCategory(undefined)}
          className={`rounded-lg px-3 py-1.5 text-label font-medium transition-colors ${
            !category ? "bg-primary-soft text-primary" : "bg-elevated text-foreground-secondary hover:text-foreground"
          }`}
        >
          All
        </button>
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(category === c ? undefined : c)}
            className={`rounded-lg px-3 py-1.5 text-label font-medium transition-colors ${
              category === c ? "bg-primary-soft text-primary" : "bg-elevated text-foreground-secondary hover:text-foreground"
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-52 rounded-xl bg-card" />
          ))}
        </div>
      ) : agents.length === 0 ? (
        <EmptyState
          icon={<Bot className="mx-auto" />}
          title="No agents match"
          description="Try a different search or filter."
          action={
            <Button variant="secondary" onClick={() => { setSearch(""); setCategory(undefined); }}>
              Clear filters
            </Button>
          }
        />
      ) : (
        <motion.div
          layout
          className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
          initial="hidden"
          animate="visible"
          variants={{
            visible: { transition: { staggerChildren: 0.05 } },
            hidden: {},
          }}
        >
          {agents.map((agent, i) => (
            <motion.div
              key={agent.agent_name}
              variants={{
                hidden: { opacity: 0, y: 12 },
                visible: { opacity: 1, y: 0 },
              }}
            >
              <AgentMarketplaceCard
                agent={agent}
                onInstall={handleInstall}
                installing={installing}
              />
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
