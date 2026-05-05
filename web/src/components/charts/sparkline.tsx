"use client";

import { Line, LineChart, ResponsiveContainer } from "recharts";

export interface SparklinePoint {
  t: number;
  v: number;
}

export function Sparkline({
  data,
  height = 28,
}: {
  data: SparklinePoint[];
  height?: number;
}) {
  if (data.length < 2) {
    return (
      <div
        className="text-[10px] text-muted-foreground"
        style={{ height }}
        aria-hidden
      >
        —
      </div>
    );
  }
  return (
    <div style={{ height }} aria-hidden>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line
            type="monotone"
            dataKey="v"
            stroke="hsl(var(--primary))"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
