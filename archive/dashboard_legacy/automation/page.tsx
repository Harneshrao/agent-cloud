"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Calendar, Plus, Bot, ArrowRight } from "lucide-react";
import { useDashboard } from "@/hooks/use-dashboard";
import { ApiConnectionBanner } from "@/components/api-connection-banner";
import { PremiumCard } from "@/components/ui/premium-card";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export default function AutomationPage() {
  const { data, loading, refetch } = useDashboard();
  const [filter, setFilter] = useState<"all" | "active">("all");

  const installations = data?.installations ?? [];

  if (loading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-9 w-64 bg-elevated" />
        <Skeleton className="h-64 rounded-xl bg-card" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-page-title text-foreground tracking-tight">
          Automation
        </h1>
        <p className="mt-2 text-body text-foreground-secondary">
          Schedule agents to run on a recurring basis. Hourly, daily, weekly, or custom CRON.
        </p>
      </motion.div>

      <ApiConnectionBanner onReady={refetch} />


      <div className="flex flex-wrap items-center gap-4">
        <div className="flex rounded-lg border border-border bg-card p-1">
          {(["all", "active"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                filter === f
                  ? "bg-primary text-white"
                  : "text-foreground-secondary hover:text-foreground"
              }`}
            >
              {f === "all" ? "All" : "Active only"}
            </button>
          ))}
        </div>
        <Button asChild>
          <Link href="/marketplace" className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Create automation
          </Link>
        </Button>
      </div>

      {installations.length === 0 ? (
        <PremiumCard>
          <EmptyState
            icon={<Calendar className="mx-auto" />}
            title="No automations yet"
            description="Install an agent from the marketplace, then add a schedule to run it automatically."
            action={
              <Button asChild>
                <Link href="/marketplace">Browse marketplace</Link>
              </Button>
            }
          />
        </PremiumCard>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {installations.map((inst) => (
            <motion.div
              key={inst.installation_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Link
                href={`/installations/${inst.installation_id}/automation`}
                className="block"
              >
                <PremiumCard className="flex flex-row items-center gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                    <Bot className="h-6 w-6" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-foreground">
                      {inst.agent_name}
                    </p>
                    <p className="text-label text-muted">
                      Configure schedule
                    </p>
                  </div>
                  <ArrowRight className="h-5 w-5 shrink-0 text-muted" />
                </PremiumCard>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
