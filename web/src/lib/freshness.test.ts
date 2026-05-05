import { describe, expect, it } from "vitest";
import { freshnessOf } from "./freshness";

const NOW = Date.UTC(2026, 4, 5, 12, 0, 0);

describe("freshnessOf", () => {
  it("returns no-data when iso is missing", () => {
    expect(freshnessOf(undefined, 15, NOW)).toBe("no-data");
    expect(freshnessOf(null, 15, NOW)).toBe("no-data");
    expect(freshnessOf("", 15, NOW)).toBe("no-data");
  });

  it("returns no-data for unparseable input", () => {
    expect(freshnessOf("not-a-date", 15, NOW)).toBe("no-data");
  });

  it("returns fresh below the 4× threshold", () => {
    const iso = new Date(NOW - 30_000).toISOString(); // 30 s ago
    expect(freshnessOf(iso, 15, NOW)).toBe("fresh");
  });

  it("returns stale above the 4× threshold", () => {
    const iso = new Date(NOW - 61_000).toISOString(); // 61 s ago
    expect(freshnessOf(iso, 15, NOW)).toBe("stale");
  });

  it("treats the boundary (exactly 4× poll) as stale", () => {
    const iso = new Date(NOW - 60_000).toISOString(); // 60 s ago
    expect(freshnessOf(iso, 15, NOW)).toBe("stale");
  });
});
