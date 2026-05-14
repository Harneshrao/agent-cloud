"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Save, Play } from "lucide-react";
import { fetchInstallation, updateConfiguration, runInstallation } from "@/lib/api";
import type { Installation } from "@/types";
import { GlassCard } from "@/components/product/glass-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

export default function ConfigurePage({
  params,
}: {
  params: Promise<{ id?: string }>;
}) {
  const router = useRouter();
  const resolved = React.use(params);
  const id = Number(resolved.id);
  const [inst, setInst] = useState<Installation | null>(null);
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await fetchInstallation(id);
        if (!cancelled) {
          setInst(data);
          setConfig((data.configuration as Record<string, unknown>) || {});
        }
      } catch {
        if (!cancelled) setInst(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
  }, [id]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateConfiguration(id, config);
      const data = await fetchInstallation(id);
      setInst(data);
      setConfig((data.configuration as Record<string, unknown>) || {});
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    try {
      await runInstallation(id);
      router.push("/");
    } finally {
      setRunning(false);
    }
  };

  const schema = (inst?.input_schema || {}) as Record<
    string,
    { type?: string; default?: unknown; required?: boolean }
  >;
  const keys = Object.keys(schema);

  if (loading || !inst) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-96 rounded-2xl" />
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
          Configure {inst.agent_name}
        </h1>
        <p className="mt-1 text-neutral-400">
          Set inputs once. Run anytime with one click.
        </p>
      </motion.div>

      <GlassCard className="p-6 max-w-2xl">
        <h2 className="text-lg font-semibold text-foreground">Inputs</h2>
        <p className="text-sm text-neutral-500 mt-0.5">
          These values are sent when you run the agent.
        </p>

        {keys.length === 0 ? (
          <p className="mt-6 text-sm text-neutral-500">
            This agent has no configurable inputs. You can run it as is.
          </p>
        ) : (
          <div className="mt-6 space-y-5">
            {keys.map((key) => (
              <div key={key}>
                <Label className="text-foreground">
                  {key.replace(/_/g, " ")}
                  {(schema[key]?.required && " *") || ""}
                </Label>
                <Input
                  className="mt-1.5 rounded-xl bg-white/5 border-white/10"
                  value={(config[key] as string) ?? ""}
                  onChange={(e) =>
                    setConfig((c) => ({ ...c, [key]: e.target.value }))
                  }
                  placeholder={
                    schema[key]?.default != null
                      ? String(schema[key].default)
                      : undefined
                  }
                />
              </div>
            ))}
          </div>
        )}

        <div className="mt-8 flex flex-wrap gap-3">
          <Button onClick={handleSave} disabled={saving} variant="secondary">
            {saving ? "Saving…" : "Save configuration"}
          </Button>
          <Button onClick={handleRun} disabled={running}>
            {running ? "Starting…" : "Test run"}
          </Button>
        </div>
      </GlassCard>
    </div>
  );
}
