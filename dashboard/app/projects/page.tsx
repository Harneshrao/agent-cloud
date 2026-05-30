"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useActiveProject } from "@/context/active-project";
import { createProject } from "@/lib/api";
import { friendlyApiError } from "@/lib/project-messages";
import { GlassCard } from "@/components/product/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ProjectsPage() {
  const {
    projects,
    projectId,
    loading,
    refreshProjects,
    setProject,
  } = useActiveProject();
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refreshProjects();
  }, [refreshProjects]);

  const onCreate = async () => {
    const n = name.trim();
    if (!n) return;
    setCreating(true);
    setError(null);
    try {
      const res = await createProject(n);
      const id = res.project?.id;
      if (id) setProject(id);
      setName("");
      await refreshProjects();
    } catch (e) {
      setError(friendlyApiError(e instanceof Error ? e.message : "Failed to create project"));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">Projects</h1>
        <p className="mt-1 max-w-lg text-neutral-400">
          A project is your workspace — deployments, runs, and billing all live here. We remember
          your selection automatically.
        </p>
      </div>

      <GlassCard className="p-6">
        <div className="text-sm font-medium text-foreground">Create a project</div>
        <p className="mt-1 text-xs text-neutral-500">Takes a few seconds. Name it anything you like.</p>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. my-first-agents"
            className="sm:max-w-md"
          />
          <Button type="button" onClick={() => void onCreate()} disabled={creating || !name.trim()}>
            {creating ? "Creating…" : "Create project"}
          </Button>
        </div>
      </GlassCard>

      {error ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      ) : null}

      {loading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : (
        <GlassCard className="overflow-hidden">
          {projects.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-neutral-400">No projects yet — create one above to continue.</p>
            </div>
          ) : (
            <ul className="divide-y divide-white/5">
              {projects.map((p) => (
                <li key={p.id} className="px-6 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="font-medium text-foreground">{p.name}</div>
                      <div className="mt-1 text-xs text-neutral-500">Active in top bar when selected</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant={projectId === p.id ? "default" : "outline"}
                        onClick={() => setProject(p.id)}
                      >
                        {projectId === p.id ? "Active" : "Use this project"}
                      </Button>
                      <Link
                        href="/deployments"
                        className="text-sm text-primary hover:underline"
                      >
                        Deploy →
                      </Link>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>
      )}
    </div>
  );
}
