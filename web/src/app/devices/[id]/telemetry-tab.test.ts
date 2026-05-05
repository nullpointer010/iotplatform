import { describe, expect, it } from "vitest";
import { buildCsv } from "./telemetry-tab";

describe("buildCsv", () => {
  it("emits the header row even with no entries", () => {
    expect(buildCsv([])).toBe("dateObserved,numValue,unitCode");
  });

  it("emits one row per entry; empty unit becomes blank", () => {
    const csv = buildCsv([
      { dateObserved: "2026-05-05T10:00:00Z", numValue: 21.5, unitCode: "CEL" },
      { dateObserved: "2026-05-05T10:00:10Z", numValue: 21.7, unitCode: null },
    ]);
    expect(csv.split("\n")).toEqual([
      "dateObserved,numValue,unitCode",
      "2026-05-05T10:00:00Z,21.5,CEL",
      "2026-05-05T10:00:10Z,21.7,",
    ]);
  });
});
