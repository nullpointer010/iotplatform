import { describe, expect, it } from "vitest";
import { assertRole, type Me } from "./auth";

const me = (roles: string[]): Me => ({ username: "u", sub: "s", roles });

describe("assertRole (UI defence-in-depth)", () => {
  it("admin is an implicit superuser", () => {
    expect(() => assertRole(me(["admin"]), "operator")).not.toThrow();
    expect(() => assertRole(me(["admin"]))).not.toThrow(); // empty allowed
  });

  it("matches when the user has the role", () => {
    expect(() => assertRole(me(["operator"]), "operator")).not.toThrow();
    expect(() =>
      assertRole(me(["maintenance_manager"]), "operator", "maintenance_manager"),
    ).not.toThrow();
  });

  it("rejects when the role is missing", () => {
    expect(() => assertRole(me(["viewer"]), "operator")).toThrow("forbidden");
    expect(() => assertRole(me(["operator"]))).toThrow("forbidden"); // admin-only
    expect(() => assertRole(undefined, "operator")).toThrow("forbidden");
  });
});
