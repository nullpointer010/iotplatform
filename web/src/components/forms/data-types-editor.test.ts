import { describe, expect, it } from "vitest";
import {
  parseDataTypes,
  serializeDataTypes,
} from "./data-types-editor";

describe("parseDataTypes", () => {
  it("returns [] for empty / invalid input", () => {
    expect(parseDataTypes(undefined)).toEqual([]);
    expect(parseDataTypes("")).toEqual([]);
    expect(parseDataTypes("not-json")).toEqual([]);
    expect(parseDataTypes("[1,2]")).toEqual([]);
  });

  it("rounds non-Number values to Text", () => {
    const rows = parseDataTypes(
      JSON.stringify({ temperature: "Number", mode: "weird" }),
    );
    expect(rows).toEqual([
      { prop: "temperature", kind: "Number" },
      { prop: "mode", kind: "Text" },
    ]);
  });
});

describe("serializeDataTypes", () => {
  it("returns undefined when there are no usable rows", () => {
    expect(serializeDataTypes([])).toBeUndefined();
    expect(serializeDataTypes([{ prop: "  ", kind: "Number" }])).toBeUndefined();
  });

  it("trims keys and produces the wire shape", () => {
    const out = serializeDataTypes([
      { prop: " temperature ", kind: "Number" },
      { prop: "mode", kind: "Text" },
    ]);
    expect(out).toBeDefined();
    expect(JSON.parse(out!)).toEqual({ temperature: "Number", mode: "Text" });
  });

  it("round-trips parse → serialize", () => {
    const json = JSON.stringify({ humidity: "Number", label: "Text" });
    const out = serializeDataTypes(parseDataTypes(json));
    expect(JSON.parse(out!)).toEqual({ humidity: "Number", label: "Text" });
  });
});
