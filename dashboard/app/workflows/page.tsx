"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { formatDate } from "@/lib/utils";
import { fetchTasks } from "@/lib/api";
import type { TaskListItem } from "@/types";
import { GitBranch, Plus } from "lucide-react";

export default function WorkflowsPage() {
  const [tasks, setTasks] = useState<TaskListItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTasks = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await fetchTasks();
      setTasks(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch");
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Workflows</h1>
          <p className="text-neutral-400 mt-1">Tasks and execution history</p>
        </div>
        <Button asChild className="btn-glow">
          <Link href="/workflows/builder" className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Workflow Builder
          </Link>
        </Button>
      </div>

      <section
        className="rounded-2xl border border-border bg-elevated/80 p-6 md:p-8"
        aria-labelledby="workflow-overview-heading"
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-8">
          <div className="space-y-2 min-w-0">
            <h2
              id="workflow-overview-heading"
              className="text-base font-semibold tracking-tight text-foreground"
            >
              Task graph
            </h2>
            <p className="text-sm text-foreground-secondary leading-relaxed max-w-xl">
              Runs enqueue to the queue; workers claim work; the orchestrator executes your DAG and
              writes history here. Use the builder to wire agents and dependencies.
            </p>
          </div>
          <ul className="shrink-0 space-y-2 text-sm text-foreground-secondary border border-border rounded-xl bg-card/50 px-4 py-3 w-full sm:w-auto sm:min-w-[220px]">
            <li className="flex items-center gap-2 text-foreground">
              <span className="size-1.5 rounded-full bg-primary" aria-hidden />
              Queue → worker → agents
            </li>
            <li className="flex items-center gap-2">
              <span className="size-1.5 rounded-full bg-foreground-secondary/50" aria-hidden />
              Status &amp; logs on each task row
            </li>
          </ul>
        </div>
      </section>

      {error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 flex items-center justify-between gap-4 flex-wrap">
          <span>Couldn’t load tasks. Showing offline list.</span>
          <Button variant="secondary" size="sm" onClick={() => loadTasks()}>
            Retry
          </Button>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <GitBranch className="h-4 w-4" />
            All tasks
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-14 rounded-xl bg-elevated" />
              ))}
            </div>
          ) : !tasks?.length ? (
            <EmptyState
              icon={<GitBranch className="h-12 w-12" />}
              title="No workflows yet"
              description="Build a chain of agents in the Workflow Builder, or run agents from the Dashboard. Executions will appear here."
              action={
                <div className="flex flex-wrap gap-2 justify-center">
                  <Button asChild className="btn-glow">
                    <Link href="/workflows/builder">Open Workflow Builder</Link>
                  </Button>
                  <Button variant="secondary" asChild>
                    <Link href="/">Dashboard</Link>
                  </Button>
                </div>
              }
            />
          ) : (
            <div className="space-y-1">
              {(tasks ?? []).map((task) => (
                <Link
                  key={task.id}
                  href={`/workflows/${task.id}`}
                  className="flex items-center justify-between rounded-xl border border-transparent px-4 py-3 transition-all hover:border-border hover:bg-elevated/60"
                >
                  <div className="min-w-0 flex-1">
                    <span className="font-medium text-foreground">Task #{task.id}</span>
                    <p className="truncate text-sm text-neutral-400 mt-0.5">
                      {typeof task.task_text === "string"
                        ? task.task_text
                        : JSON.stringify(task.task_text)}
                    </p>
                  </div>
                  <div className="ml-4 shrink-0 text-right text-sm text-neutral-500">
                    {formatDate(task.created_at)}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
