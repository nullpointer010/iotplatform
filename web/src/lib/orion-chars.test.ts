import { describe, expect, it } from "vitest";
import { findForbiddenChar } from "./orion-chars";

describe("findForbiddenChar", () => {
  it("returns null for safe input", () => {
    expect(findForbiddenChar("Juan Pérez - IFAPA")).toBeNull();
    expect(findForbiddenChar("crop/almeria/dev001")).toBeNull();
  });

  it("returns the offending character", () => {
    expect(findForbiddenChar("Juan (IFAPA)")).toBe("(");
    expect(findForbiddenChar("a=b")).toBe("=");
    expect(findForbiddenChar('he said "hi"')).toBe('"');
  });
});
