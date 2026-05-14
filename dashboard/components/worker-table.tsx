"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WorkerInfo } from "@/types";
import { formatDate } from "@/lib/utils";
import { Users } from "lucide-react";

interface WorkerTableProps {
  workers: WorkerInfo[];
}

export function WorkerTable({ workers }: WorkerTableProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Users className="h-4 w-4" />
          Worker registry
        </CardTitle>
      </CardHeader>
      <CardContent>
        {workers.length === 0 ? (
          <p className="text-sm text-neutral-500 py-8 text-center">No workers registered</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-neutral-400">
                  <th className="pb-3 font-medium">Worker ID</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Tasks running</th>
                  <th className="pb-3 font-medium">Last seen</th>
                </tr>
              </thead>
              <tbody>
                {workers.map((w) => (
                  <tr key={w.worker_id} className="border-b border-border/50">
                    <td className="py-3 font-mono text-foreground">{w.worker_id}</td>
                    <td className="py-3">
                      <span
                        className={`rounded-lg px-2 py-0.5 text-xs font-medium ${
                          w.status === "active" ? "bg-emerald-500/20 text-emerald-400" : "bg-neutral-500/20 text-neutral-400"
                        }`}
                      >
                        {w.status}
                      </span>
                    </td>
                    <td className="py-3 text-neutral-300">{w.tasks_running}</td>
                    <td className="py-3 text-neutral-500">{formatDate(w.last_seen)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
