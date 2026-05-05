import { describe, it, expect } from "vitest";
import { paginate, PAGE_SIZE } from "./paginate";

describe("paginate", () => {
  it("returns an empty single page for an empty list", () => {
    const r = paginate([], 1, 10);
    expect(r).toEqual({ page: 1, totalPages: 1, items: [] });
  });

  it("returns the requested slice", () => {
    const items = Array.from({ length: 25 }, (_, i) => i);
    const r = paginate(items, 2, 10);
    expect(r.page).toBe(2);
    expect(r.totalPages).toBe(3);
    expect(r.items).toEqual([10, 11, 12, 13, 14, 15, 16, 17, 18, 19]);
  });

  it("clamps page below 1 to 1", () => {
    const items = [1, 2, 3];
    const r = paginate(items, 0, 10);
    expect(r.page).toBe(1);
    expect(r.items).toEqual([1, 2, 3]);
  });

  it("clamps page above totalPages to totalPages", () => {
    const items = Array.from({ length: 12 }, (_, i) => i);
    const r = paginate(items, 99, 5);
    expect(r.page).toBe(3);
    expect(r.totalPages).toBe(3);
    expect(r.items).toEqual([10, 11]);
  });

  it("handles exact-boundary list sizes", () => {
    const items = Array.from({ length: 20 }, (_, i) => i);
    const r = paginate(items, 2, 10);
    expect(r.totalPages).toBe(2);
    expect(r.items).toHaveLength(10);
  });

  it("uses PAGE_SIZE when pageSize is omitted", () => {
    const items = Array.from({ length: PAGE_SIZE + 1 }, (_, i) => i);
    const r = paginate(items, 2);
    expect(r.totalPages).toBe(2);
    expect(r.items).toEqual([PAGE_SIZE]);
  });
});
