import { describe, expect, it } from "vitest";
import { classifyMarker } from "./marker-state";

const NOW = Date.parse("2026-05-05T16:00:00Z");
const RECENT = "2026-05-05T15:59:30Z"; // 30s old
const OLD = "2026-05-05T15:50:00Z"; // 10 min old

describe("classifyMarker", () => {
  it("→ no-data when there is no timestamp", () => {
    expect(classifyMarker({ deviceState: "active", lastSampleIso: null, now: NOW })).toBe("no-data");
    expect(classifyMarker({ deviceState: "active", lastSampleIso: undefined, now: NOW })).toBe("no-data");
    expect(classifyMarker({ deviceState: "active", lastSampleIso: "garbage", now: NOW })).toBe("no-data");
  });

  it("→ stale when older than the threshold (state is irrelevant)", () => {
    expect(classifyMarker({ deviceState: "active", lastSampleIso: OLD, now: NOW })).toBe("stale");
    expect(classifyMarker({ deviceState: "maintenance", lastSampleIso: OLD, now: NOW })).toBe("stale");
  });

  it("→ fresh-maintenance when fresh and in maintenance", () => {
    expect(classifyMarker({ deviceState: "maintenance", lastSampleIso: RECENT, now: NOW })).toBe("fresh-maintenance");
  });

  it("→ fresh-active when fresh and active", () => {
    expect(classifyMarker({ deviceState: "active", lastSampleIso: RECENT, now: NOW })).toBe("fresh-active");
  });

  it("→ inactive when fresh but state is inactive / unknown", () => {
    expect(classifyMarker({ deviceState: "inactive", lastSampleIso: RECENT, now: NOW })).toBe("inactive");
    expect(classifyMarker({ deviceState: null, lastSampleIso: RECENT, now: NOW })).toBe("inactive");
    expect(classifyMarker({ deviceState: "weird", lastSampleIso: RECENT, now: NOW })).toBe("inactive");
  });

  it("respects a custom staleAfterMs", () => {
    expect(
      classifyMarker({
        deviceState: "active",
        lastSampleIso: RECENT,
        staleAfterMs: 10,
        now: NOW,
      }),
    ).toBe("stale");
  });
});
