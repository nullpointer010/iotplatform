"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Activity, Cpu, Wrench } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const devices = useQuery({
    queryKey: ["devices"],
    queryFn: () => api.listDevices(1000, 0),
  });
  const opTypes = useQuery({
    queryKey: ["operation-types"],
    queryFn: () => api.listOperationTypes(),
  });

  const total = devices.data?.length ?? 0;
  const active = devices.data?.filter((d) => d.deviceState === "active").length ?? 0;
  const maintenance =
    devices.data?.filter((d) => d.deviceState === "maintenance").length ?? 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Overview of devices and platform configuration.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          title="Devices"
          value={devices.isLoading ? "…" : String(total)}
          subtitle={`${active} active · ${maintenance} in maintenance`}
          icon={<Cpu className="h-5 w-5" />}
          href="/devices"
        />
        <StatCard
          title="Operation types"
          value={opTypes.isLoading ? "…" : String(opTypes.data?.length ?? 0)}
          subtitle="Defined maintenance operations"
          icon={<Wrench className="h-5 w-5" />}
          href="/maintenance/operation-types"
        />
        <StatCard
          title="Status"
          value={devices.isError ? "API down" : "API up"}
          subtitle={
            devices.isError
              ? "Cannot reach FastAPI backend"
              : "Backend reachable"
          }
          icon={<Activity className="h-5 w-5" />}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick actions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Link
            href="/devices/new"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Register a device
          </Link>
          <Link
            href="/maintenance/operation-types"
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent"
          >
            Manage operation types
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  title,
  value,
  subtitle,
  icon,
  href,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  href?: string;
}) {
  const inner = (
    <Card className="transition-colors hover:bg-accent/40">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className="text-muted-foreground">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-semibold">{value}</div>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </CardContent>
    </Card>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}
