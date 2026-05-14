"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// Mock data for "tasks per minute" - in production this would come from an API
const generateMockTasksPerMinute = () => {
  const now = new Date();
  return Array.from({ length: 24 }, (_, i) => {
    const d = new Date(now);
    d.setMinutes(d.getMinutes() - (23 - i));
    return {
      time: d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }),
      tasks: Math.round(10 + Math.random() * 20 + Math.sin(i / 3) * 5),
    };
  });
};

export function TasksChart() {
  const data = useMemo(() => generateMockTasksPerMinute(), []);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-medium">Tasks per minute</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[240px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="tasksGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" vertical={false} />
              <XAxis dataKey="time" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#666" fontSize={11} tickLine={false} axisLine={false} width={28} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #2a2a2a",
                  borderRadius: "12px",
                }}
                labelStyle={{ color: "#fafafa" }}
                formatter={(value: number) => [value, "Tasks"]}
              />
              <Area
                type="monotone"
                dataKey="tasks"
                stroke="var(--accent)"
                strokeWidth={2}
                fill="url(#tasksGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
