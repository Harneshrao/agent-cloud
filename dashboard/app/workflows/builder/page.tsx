"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, GitBranch } from "lucide-react";
import { WorkflowBuilderCanvas } from "@/components/workflow/workflow-builder-canvas";
import { fetchInstallations } from "@/lib/api";
import type { Installation } from "@/types";

export default function WorkflowBuilderPage() {
  const [installations, setInstallations] = useState<Installation[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInstallations();
      setInstallations(data.installations ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load agents");
      setInstallations([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/workflows">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <GitBranch className="h-7 w-7 text-primary" />
            Workflow Builder
          </h1>
          <p className="text-foreground-secondary mt-1">
            Chain agents: drag steps onto the canvas and connect them to define execution order.
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 flex items-center justify-between gap-4 flex-wrap">
          <span>Couldn’t load installed agents. You can still build a workflow and run when the server is available.</span>
          <Button variant="secondary" size="sm" onClick={load}>
            Retry
          </Button>
        </div>
      )}

      {loading ? (
        <Skeleton className="h-[520px] rounded-2xl bg-elevated" />
      ) : (
        <WorkflowBuilderCanvas installations={installations ?? []} />
      )}
    </div>
  );
}
