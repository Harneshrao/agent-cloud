"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { fetchSchedules, createSchedule, disableSchedule } from "@/lib/api";
import type { ScheduleItem } from "@/types";
import { formatDate } from "@/lib/utils";
import { Calendar, Plus, Trash2 } from "lucide-react";

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<ScheduleItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [taskText, setTaskText] = useState("");
  const [cron, setCron] = useState("0 * * * *");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    try {
      const data = await fetchSchedules();
      setSchedules(data.schedules ?? []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load schedules");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await createSchedule({
        task_text: taskText,
        cron_expression: cron,
        enabled: true,
      });
      setTaskText("");
      setCron("0 * * * *");
      setCreateOpen(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create schedule");
    } finally {
      setCreating(false);
    }
  };

  const handleDisable = async (id: number) => {
    try {
      await disableSchedule(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to disable schedule");
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Schedules</h1>
          <p className="text-neutral-400 mt-1">Cron-based task scheduling</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New schedule
        </Button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Scheduled tasks
          </CardTitle>
        </CardHeader>
        <CardContent>
          {schedules === null ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16 rounded-xl" />
              ))}
            </div>
          ) : schedules.length === 0 ? (
            <EmptyState
              icon={<Calendar className="h-12 w-12" />}
              title="No schedules"
              description="Create an automation to run tasks on a cron schedule (e.g. every hour or daily)."
              action={
                <Button onClick={() => setCreateOpen(true)}>
                  Create schedule
                </Button>
              }
            />
          ) : (
            <div className="space-y-2">
              {schedules.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between rounded-xl border border-border px-4 py-3"
                >
                  <div>
                    <p className="font-medium text-foreground">{s.task_text}</p>
                    <p className="text-sm text-neutral-500 mt-0.5">
                      Cron: {s.cron_expression}
                      {s.agent && ` · Agent: ${s.agent}`}
                    </p>
                    <p className="text-xs text-neutral-600 mt-1">
                      Last run: {formatDate(s.last_run_at ?? null)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-lg px-2 py-1 text-xs font-medium ${
                        s.enabled ? "bg-emerald-500/20 text-emerald-400" : "bg-neutral-500/20 text-neutral-400"
                      }`}
                    >
                      {s.enabled ? "Enabled" : "Disabled"}
                    </span>
                    {s.enabled && (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDisable(s.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New schedule</DialogTitle>
            <DialogDescription>
              Create a recurring task with a cron expression (e.g. every hour: 0 * * * *).
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="task_text">Task text</Label>
              <Input
                id="task_text"
                value={taskText}
                onChange={(e) => setTaskText(e.target.value)}
                placeholder="Task to run"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cron">Cron expression</Label>
              <Input
                id="cron"
                value={cron}
                onChange={(e) => setCron(e.target.value)}
                placeholder="0 * * * *"
                required
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={creating}>
                {creating ? "Creating…" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
