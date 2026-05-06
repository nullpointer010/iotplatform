/**
 * Map a chart range to QuantumLeap aggregation params.
 *
 * Ticket 0021c — bucketing strategy:
 *  - 1h:  raw  (no aggregation; backend caps at lastN=1000)
 *  - 24h: avg per minute (1 440 buckets)
 *  - 7d:  avg per hour   (168 buckets)
 *  - custom: auto by span
 *      ≤ 2 h  → second
 *      ≤ 2 d  → minute
 *      ≤ 30 d → hour
 *      > 30 d → day
 *  - When the helper returns ``aggrMethod === "avg"``, the route
 *    fans out three QL calls (avg/min/max) so the chart can draw
 *    a min/max envelope.
 */

export type TimeSeriesRange = "1h" | "24h" | "7d" | "custom";

export type AggrPeriod = "second" | "minute" | "hour" | "day";

export interface AggregationChoice {
  aggrMethod: "none" | "avg";
  aggrPeriod?: AggrPeriod;
}

const HOUR = 3_600_000;
const DAY = 24 * HOUR;

export function pickAggregation(
  range: TimeSeriesRange,
  fromIso?: string,
  toIso?: string,
): AggregationChoice {
  if (range === "1h") return { aggrMethod: "none" };
  if (range === "24h") return { aggrMethod: "avg", aggrPeriod: "minute" };
  if (range === "7d") return { aggrMethod: "avg", aggrPeriod: "hour" };

  // custom
  if (!fromIso || !toIso) {
    return { aggrMethod: "avg", aggrPeriod: "hour" };
  }
  const span = new Date(toIso).getTime() - new Date(fromIso).getTime();
  if (!Number.isFinite(span) || span <= 0) {
    return { aggrMethod: "avg", aggrPeriod: "hour" };
  }
  if (span <= 2 * HOUR) return { aggrMethod: "avg", aggrPeriod: "second" };
  if (span <= 2 * DAY) return { aggrMethod: "avg", aggrPeriod: "minute" };
  if (span <= 30 * DAY) return { aggrMethod: "avg", aggrPeriod: "hour" };
  return { aggrMethod: "avg", aggrPeriod: "day" };
}
