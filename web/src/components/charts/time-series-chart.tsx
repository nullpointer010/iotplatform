"use client";

import { format } from "date-fns";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface TimeSeriesPoint {
  t: number;
  v: number;
}

export type TimeSeriesRange = "1h" | "24h" | "7d" | "custom";

export function TimeSeriesChart({
  data,
  range,
  unit,
  height = 280,
}: {
  data: TimeSeriesPoint[];
  range: TimeSeriesRange;
  unit?: string | null;
  height?: number;
}) {
  const xFmt = (t: number) => {
    const d = new Date(t);
    if (range === "1h" || range === "24h") return format(d, "HH:mm");
    return format(d, "dd MMM");
  };
  const tipFmt = (t: number) =>
    format(
      new Date(t),
      range === "1h" || range === "24h" ? "dd MMM HH:mm" : "dd MMM yyyy HH:mm",
    );

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis
            dataKey="t"
            tickFormatter={xFmt}
            type="number"
            domain={["dataMin", "dataMax"]}
            scale="time"
            tick={{ fontSize: 11 }}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            label={
              unit
                ? { value: unit, angle: -90, position: "insideLeft", fontSize: 11 }
                : undefined
            }
          />
          <Tooltip
            labelFormatter={(l) => tipFmt(Number(l))}
            formatter={(v) => [unit ? `${v} ${unit}` : String(v), "value"]}
          />
          <Line
            type="monotone"
            dataKey="v"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
