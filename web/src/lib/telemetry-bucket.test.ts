import { describe, it, expect } from "vitest";
import { pickAggregation } from "./telemetry-bucket";

const HOUR = 3_600_000;
const DAY = 24 * HOUR;

function isoOffset(ms: number): string {
  return new Date(Date.now() - ms).toISOString();
}

describe("pickAggregation", () => {
  it("1h → raw", () => {
    expect(pickAggregation("1h")).toEqual({ aggrMethod: "none" });
  });

  it("24h → avg/minute", () => {
    expect(pickAggregation("24h")).toEqual({
      aggrMethod: "avg",
      aggrPeriod: "minute",
    });
  });

  it("7d → avg/hour", () => {
    expect(pickAggregation("7d")).toEqual({
      aggrMethod: "avg",
      aggrPeriod: "hour",
    });
  });

  it("custom without dates → avg/hour fallback", () => {
    expect(pickAggregation("custom")).toEqual({
      aggrMethod: "avg",
      aggrPeriod: "hour",
    });
  });

  it("custom 1h span → second", () => {
    const to = new Date().toISOString();
    const from = isoOffset(HOUR);
    expect(pickAggregation("custom", from, to)).toEqual({
      aggrMethod: "avg",
      aggrPeriod: "second",
    });
  });

  it("custom 1d span → minute", () => {
    const to = new Date().toISOString();
    const from = isoOffset(DAY);
    expect(pickAggregation("custom", from, to)).toEqual({
      aggrMethod: "avg",
      aggrPeriod: "minute",
    });
  });

  it("custom 10d span → hour", () => {
    const to = new Date().toISOString();
    const from = isoOffset(10 * DAY);
    expect(pickAggregation("custom", from, to)).toEqual({
      aggrMethod: "avg",
      aggrPeriod: "hour",
    });
  });

  it("custom 60d span → day", () => {
    const to = new Date().toISOString();
    const from = isoOffset(60 * DAY);
    expect(pickAggregation("custom", from, to)).toEqual({
      aggrMethod: "avg",
      aggrPeriod: "day",
    });
  });

  it("custom inverted range → fallback hour", () => {
    const from = new Date().toISOString();
    const to = isoOffset(DAY);
    expect(pickAggregation("custom", from, to)).toEqual({
      aggrMethod: "avg",
      aggrPeriod: "hour",
    });
  });
});
