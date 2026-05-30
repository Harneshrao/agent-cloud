"use client";

import Link from "next/link";
import { useActiveProject } from "@/context/active-project";
import { Search, UserCircle2 } from "lucide-react";

export function Topbar() {
  const { projects, projectId, projectName, setProject, loading } = useActiveProject();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-6 border-b border-border bg-background/75 px-6 backdrop-blur">
      <div className="flex flex-1 items-center gap-4">
        <div className="min-w-[200px]">
          <label className="sr-only" htmlFor="project-select">
            Active project
          </label>
          <select
            id="project-select"
            value={projectId}
            disabled={loading}
            onChange={(e) => setProject(e.target.value)}
            className="h-10 w-full max-w-xs rounded-lg border border-border bg-card px-3 text-sm text-foreground"
          >
            <option value="">
              {loading ? "Loading projects…" : "Select project…"}
            </option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {projectName ? (
            <p className="mt-0.5 text-[11px] text-neutral-500">Active: {projectName}</p>
          ) : (
            <p className="mt-0.5 text-[11px] text-amber-600">
              <Link href="/projects" className="hover:underline">
                Create a project
              </Link>{" "}
              to get started
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Link
          href="/api-keys"
          className="hidden text-sm text-neutral-500 hover:text-primary sm:inline"
        >
          API keys
        </Link>
        <button
          type="button"
          className="inline-flex h-10 items-center gap-2 rounded-xl border border-border/60 bg-card px-3 text-sm font-medium text-foreground"
          aria-label="Account"
        >
          <UserCircle2 className="h-5 w-5 text-muted" />
          <span className="hidden sm:inline">Account</span>
        </button>
      </div>
    </header>
  );
}
