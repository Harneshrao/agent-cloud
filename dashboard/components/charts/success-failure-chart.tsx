"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = {
  success: "#22c55e",
  failed: "#ef4444",
  running: "#3b82f6",
  pending: "#6b7280",
};

interface SuccessFailureChartProps {
  success?: number;
  failed?: number;
  running?: number;
  pending?: number;
}

export function SuccessFailureChart({
  success = 0,
  failed = 0,
  running = 0,
  pending = 0,
}: SuccessFailureChartProps) {
  const data = [
    { name: "Completed", value: success, color: COLORS.success },
    { name: "Failed", value: failed, color: COLORS.failed },
    { name: "Running", value: running, color: COLORS.running },
    { name: "Pending", value: pending, color: COLORS.pending },
  ].filter((d) => d.value > 0);

  const chartData =
    data.length === 0 ? [{ name: "No data", value: 1, color: COLORS.pending }] : data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-medium">Workflow outcome</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[240px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={56}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
                nameKey="name"
                label={({ name, value }) => `${name}: ${value}`}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #2a2a2a",
                  borderRadius: "12px",
                }}
              />
              <Legend
                formatter={(value, entry) => (
                  <span style={{ color: "#e5e5e5", fontSize: 12 }}>{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
