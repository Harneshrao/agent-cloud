"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis } from "recharts";
import type { ContainerInfo } from "@/types";
import { Container } from "lucide-react";

interface ContainerUtilizationProps {
  data: ContainerInfo;
}

export function ContainerUtilization({ data }: ContainerUtilizationProps) {
  const total = data.containers_idle + data.containers_busy;
  const chartData = [
    { name: "Idle", count: data.containers_idle, fill: "#6366f1" },
    { name: "Busy", count: data.containers_busy, fill: "#22c55e" },
  ].filter((d) => d.count > 0);

  if (chartData.length === 0) {
    chartData.push({ name: "None", count: 0, fill: "#2a2a2a" });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Container className="h-4 w-4" />
          Container pool
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex gap-4 text-sm">
          <span className="text-neutral-400">
            Idle: <strong className="text-foreground">{data.containers_idle}</strong>
          </span>
          <span className="text-neutral-400">
            Busy: <strong className="text-foreground">{data.containers_busy}</strong>
          </span>
          <span className="text-neutral-500">
            Total: {total}
          </span>
        </div>
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 24 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" width={48} stroke="#666" fontSize={12} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
