"use client";

import * as React from "react";
import { useHasRole } from "@/lib/auth";

/**
 * Renders `children` when the user has any of `roles`, or is admin.
 * Empty `roles` means admin-only (matches the API's `require_roles()`).
 */
export function Gate({
  roles,
  children,
  fallback = null,
}: {
  roles: string[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const ok = useHasRole(...roles);
  return <>{ok ? children : fallback}</>;
}
