"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "./api";

export type Me = { username: string; sub: string; roles: string[] };

export function useMe() {
  return useQuery<Me>({
    queryKey: ["me"],
    queryFn: () => api.me(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

/**
 * Returns true when the current user has any of `roles`, OR is `admin`
 * (implicit superuser, mirroring the API's `require_roles`).
 *
 * Calling with no arguments means "admin only" — same convention as
 * the API: `require_roles()` allows admin only.
 */
export function useHasRole(...roles: string[]): boolean {
  const { data } = useMe();
  if (!data) return false;
  if (data.roles.includes("admin")) return true;
  return roles.some((r) => data.roles.includes(r));
}

/**
 * Defence-in-depth runtime guard for destructive client-side actions.
 * The API is the source of truth; this exists so a stray button can't
 * fire its mutation if the role check above slipped through.
 */
export function assertRole(me: Me | undefined, ...roles: string[]): void {
  if (!me) throw new Error("forbidden");
  if (me.roles.includes("admin")) return;
  if (!roles.some((r) => me.roles.includes(r))) {
    throw new Error("forbidden");
  }
}
