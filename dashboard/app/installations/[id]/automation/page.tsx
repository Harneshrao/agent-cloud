"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Calendar, ToggleLeft, ToggleRight } from "lucide-react";
import {
  fetchInstallation,
  fetchInstallationSchedules,
  createInstallationSchedule,
  updateScheduleStatus,
} from "@/lib/api";
import type { Installation, AgentSchedule } from "@/types";
import { GlassCard } from "@/components/product/glass-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const PRESETS: { label: string; cron: string; desc: string }[] = [
  { label: "Hourly", cron: "0 * * * *", desc: "Every hour at :00" },
  { label: "Daily 9 AM", cron: "0 9 * * *", desc: "Every day at 9:00 AM" },
  { label: "Daily 6 PM", cron: "0 18 * * *", desc: "Every day at 6:00 PM" },
  { label: "Weekly Monday", cron: "0 9 * * 1", desc: "Every Monday at 9:00 AM" },
];

export default function AutomationPage({
  params,
}: {
  params: Promise<{ id?: string }>;
}) {
  const resolved = React.use(params);
  const id = Number(resolved.id);
  const [inst, setInst] = useState<Installation | null>(null);
  const [schedules, setSchedules] = useState<AgentSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState<string | null>(null);
  const [toggling, setToggling] = useState<number | null>(null);

  const load = async () => {
    try {
      const [instRes, schedRes] = await Promise.all([
        fetchInstallation(id),
        fetchInstallationSchedules(id),
      ]);
      setInst(instRes);
      setSchedules(schedRes.schedules);
    } catch {
      setInst(null);
      setSchedules([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    load();
    return () => { cancelled = true; };
  }, [id]);

  const handleCreate = async (cron: string) => {
    setCreating(cron);
    try {
      await createInstallationSchedule(id, cron, "active");
      await load();
    } finally {
      setCreating(null);
    }
  };

  const handleToggle = async (scheduleId: number, currentStatus: string) => {
    setToggling(scheduleId);
    try {
      const next = currentStatus === "active" ? "paused" : "active";
      await updateScheduleStatus(scheduleId, next);
      await load();
    } finally {
      setToggling(null);
    }
  };

  if (loading || !inst) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-64 rounded-2xl" />
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
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-neutral-400 hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Home
        </Link>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Automation — {inst.agent_name}
        </h1>
        <p className="mt-1 text-neutral-400">
          Run this agent automatically on a schedule.
        </p>
      </motion.div>

      <GlassCard className="p-6">
        <h2 className="text-lg font-semibold text-foreground">Quick schedules</h2>
        <p className="text-sm text-neutral-500 mt-0.5">
          Add a schedule to run the agent automatically.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PRESETS.map((p) => (
            <div
              key={p.cron}
              className="rounded-xl border border-white/5 bg-white/[0.02] p-4 flex flex-col"
            >
              <p className="font-medium text-foreground">{p.label}</p>
              <p className="text-sm text-neutral-500 mt-0.5">{p.desc}</p>
              <Button
                size="sm"
                variant="secondary"
                className="mt-4"
                onClick={() => handleCreate(p.cron)}
                disabled={creating === p.cron}
              >
                {creating === p.cron ? "Adding…" : "Enable"}
              </Button>
            </div>
          ))}
        </div>
      </GlassCard>

      <GlassCard className="p-6">
        <h2 className="text-lg font-semibold text-foreground">Active schedules</h2>
        <p className="text-sm text-neutral-500 mt-0.5">Cron preview: when the agent runs.</p>
        {schedules.length === 0 ? (
          <p className="mt-6 text-sm text-neutral-500">
            No schedules yet. Add one above.
          </p>
        ) : (
          <ul className="mt-6 space-y-4">
            {schedules.map((s) => (
              <li
                key={s.schedule_id}
                className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] p-4"
              >
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-neutral-500" />
                  <div>
                    <p className="font-medium text-foreground font-mono text-sm">
                      {s.cron_expression}
                    </p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      Last run: {s.last_run_at || "—"}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleToggle(s.schedule_id, s.status)}
                  disabled={toggling === s.schedule_id}
                  className="flex items-center gap-2 text-sm"
                >
                  {s.status === "active" ? (
                    <>
                      <ToggleRight className="h-5 w-5 text-accent" />
                      <span className="text-foreground">On</span>
                    </>
                  ) : (
                    <>
                      <ToggleLeft className="h-5 w-5 text-neutral-500" />
                      <span className="text-neutral-500">Paused</span>
                    </>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </GlassCard>
    </div>
  );
}
