"use client";

import { Badge } from "@/components/ui/badge";

type Variant = "default" | "secondary" | "success" | "warning";

const VARIANT: Record<string, Variant> = {
  admin: "success",
  maintenance_manager: "warning",
  operator: "default",
  viewer: "secondary",
};

const LABEL: Record<string, string> = {
  admin: "admin",
  maintenance_manager: "manager",
  operator: "operator",
  viewer: "viewer",
};

/**
 * Picks the most-privileged role to display: admin > manager > operator > viewer.
 */
function primaryRole(roles: string[]): string | undefined {
  const order = ["admin", "maintenance_manager", "operator", "viewer"];
  return order.find((r) => roles.includes(r));
}

export function RoleBadge({ roles }: { roles: string[] }) {
  const r = primaryRole(roles);
  if (!r) return null;
  return (
    <Badge variant={VARIANT[r] ?? "secondary"} className="text-[10px]">
      {LABEL[r] ?? r}
    </Badge>
  );
}
