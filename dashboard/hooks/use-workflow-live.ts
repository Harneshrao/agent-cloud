"use client";

import { useEffect, useState, useRef } from "react";
import { fetchWorkflow } from "@/lib/api";
import type { WorkflowView } from "@/types";

const POLL_MS = 2000;

export function useWorkflowLive(taskId: number | null): {
  workflow: WorkflowView | null;
  error: string | null;
} {
  const [workflow, setWorkflow] = useState<WorkflowView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (taskId == null || Number.isNaN(taskId)) return;
    let mounted = true;

    const load = async () => {
      try {
        const data = await fetchWorkflow(taskId);
        if (mounted) {
          setWorkflow(data);
          setError(null);
        }
      } catch (e) {
        if (mounted) setError(e instanceof Error ? e.message : "Failed to load workflow");
      }
    };

    load();
    intervalRef.current = setInterval(load, POLL_MS);
    return () => {
      mounted = false;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [taskId]);

  return { workflow, error };
}
