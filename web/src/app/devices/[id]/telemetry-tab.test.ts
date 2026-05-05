import { describe, expect, it } from "vitest";
import { buildCsv } from "./telemetry-tab";

describe("buildCsv", () => {
  it("emits the header row even with no entries", () => {
    expect(buildCsv([])).toBe("dateObserved,localTime,numValue,unitCode");
  });

  it("emits one row per entry; empty unit becomes blank", () => {
    const csv = buildCsv([
      { dateObserved: "2026-05-05T10:00:00Z", numValue: 21.5, unitCode: "CEL" },
      { dateObserved: "2026-05-05T10:00:10Z", numValue: 21.7, unitCode: null },
    ]);
    const lines = csv.split("\n");
    expect(lines[0]).toBe("dateObserved,localTime,numValue,unitCode");
    // Local-time column is environment-dependent; only assert the
    // ISO + numValue + unit columns.
    const cols0 = lines[1].split(",");
    expect(cols0[0]).toBe("2026-05-05T10:00:00Z");
    expect(cols0[2]).toBe("21.5");
    expect(cols0[3]).toBe("CEL");
    const cols1 = lines[2].split(",");
    expect(cols1[0]).toBe("2026-05-05T10:00:10Z");
    expect(cols1[3]).toBe("");
  });
});
