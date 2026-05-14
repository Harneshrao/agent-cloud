"use client";

import * as React from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft } from "lucide-react";
import { fetchWorkflow } from "@/lib/api";
import { FlowView } from "@/components/workflow/flow-view";
import { WorkflowTimeline } from "@/components/workflow/workflow-timeline";
import { useWorkflowLive } from "@/hooks/use-workflow-live";
import type { WorkflowView } from "@/types";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

export default function WorkflowDetailPage({
  params,
}: {
  params: Promise<{ task_id?: string }>;
}) {
  const resolved = React.use(params);
  const taskId = Number(resolved.task_id);
  const { workflow: liveWorkflow, error: liveError } = useWorkflowLive(
    Number.isNaN(taskId) ? null : taskId
  );
  const [workflow, setWorkflow] = useState<WorkflowView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (Number.isNaN(taskId)) return;
    const load = async () => {
      try {
        const data = await fetchWorkflow(taskId);
        setWorkflow(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Workflow not found");
      }
    };
    load();
  }, [taskId]);

  const displayWorkflow = liveWorkflow ?? workflow;
  const displayError = liveError ?? error;

  if (Number.isNaN(taskId)) {
    return (
      <div className="space-y-6">
        <p className="text-red-400">Invalid task ID</p>
        <Button variant="secondary" asChild>
          <Link href="/workflows">Back to workflows</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/workflows">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Workflow #{taskId}</h1>
          <p className="text-neutral-400 mt-1">Execution graph and status</p>
        </div>
      </div>

      {displayError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {displayError}
        </div>
      )}

      {displayWorkflow === null && !displayError ? (
        <Skeleton className="h-[500px] rounded-2xl" />
      ) : displayWorkflow ? (
        <>
          <Card className="transition-all duration-300 hover:shadow-soft">
            <CardHeader>
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-neutral-400">
                <span className="text-foreground">Status:</span>{" "}
                <span
                  className={cn(
                    "font-medium capitalize",
                    displayWorkflow.status === "completed" && "text-emerald-400",
                    displayWorkflow.status === "running" && "text-blue-400",
                    displayWorkflow.status === "failed" && "text-red-400"
                  )}
                >
                  {displayWorkflow.status}
                </span>
              </p>
              {displayWorkflow.retry_count > 0 && (
                <p className="text-sm text-neutral-400">
                  Retries: {displayWorkflow.retry_count}
                </p>
              )}
              {displayWorkflow.task_text && (
                <p className="text-sm text-neutral-400 truncate max-w-2xl">
                  Task: {displayWorkflow.task_text}
                </p>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-8 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <h2 className="text-lg font-medium mb-4">Execution graph</h2>
              <FlowView workflow={displayWorkflow} />
            </div>
            <div>
              <Card className="sticky top-24">
                <CardContent className="pt-6">
                  <WorkflowTimeline workflow={displayWorkflow} />
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="space-y-3">
            <h2 className="text-lg font-medium">Node results</h2>
            <div className="text-sm text-neutral-400">
              Status, output, and logs (when available) for each node in this demo workflow.
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              {displayWorkflow.child_tasks.map((n) => {
                const status = n.status;
                const title = n.node_id ? n.node_id : `Node task #${n.task_id}`;
                const outputText =
                  typeof n.output === "string"
                    ? n.output
                    : n.output == null
                      ? ""
                      : JSON.stringify(n.output, null, 2);

                const logs = n.logs ?? [];
                return (
                  <Card key={`${n.node_id ?? ""}-${n.task_id}`} className="overflow-hidden">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">{title}</CardTitle>
                      <div className="mt-2 text-xs text-neutral-400 capitalize">Status: {status}</div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div>
                        <div className="text-xs text-neutral-500 mb-2">Output</div>
                        {outputText ? (
                          <pre className="max-h-36 overflow-auto rounded-xl border border-border bg-card p-3 text-xs whitespace-pre-wrap">
                            {outputText}
                          </pre>
                        ) : (
                          <div className="text-xs text-neutral-500">—</div>
                        )}
                      </div>
                      <div>
                        <div className="text-xs text-neutral-500 mb-2">Logs</div>
                        {logs.length > 0 ? (
                          <pre className="max-h-28 overflow-auto rounded-xl border border-border bg-card p-3 text-[11px] whitespace-pre-wrap">
                            {logs
                              .map((ev) => {
                                const msg =
                                  (ev as any).message ?? (ev as any).event ?? (ev as any).type ?? "event";
                                return typeof msg === "string" ? msg : JSON.stringify(ev);
                              })
                              .join("\n")}
                          </pre>
                        ) : (
                          <div className="text-xs text-neutral-500">No logs yet.</div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
