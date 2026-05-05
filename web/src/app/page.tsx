"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Activity, Cpu, Wrench } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Gate } from "@/components/gate";
import { RecentMeasurements } from "@/components/dashboard/recent-measurements";
import { useHasRole } from "@/lib/auth";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const t = useTranslations();
  const isManager = useHasRole("maintenance_manager");
  const devices = useQuery({
    queryKey: ["devices"],
    queryFn: () => api.listDevices(1000, 0),
  });
  const opTypes = useQuery({
    queryKey: ["operation-types"],
    queryFn: () => api.listOperationTypes(),
  });

  const list = devices.data ?? [];
  const total = list.length;
  const active = list.filter((d) => d.deviceState === "active").length;
  const maintenance = list.filter((d) => d.deviceState === "maintenance").length;
  const protocolCounts = list.reduce<Record<string, number>>((acc, d) => {
    const k = d.supportedProtocol ?? "—";
    acc[k] = (acc[k] ?? 0) + 1;
    return acc;
  }, {});
  const protocolEntries = Object.entries(protocolCounts).sort((a, b) => b[1] - a[1]);
  const apiDown = devices.isError;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("dashboard.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("dashboard.subtitle")}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          title={t("dashboard.devicesCard")}
          value={devices.isLoading ? "…" : String(total)}
          subtitle={t("dashboard.devicesSubtitle", { active, maintenance })}
          icon={<Cpu className="h-5 w-5" />}
          href="/devices"
        />
        <StatCard
          title={t("dashboard.opTypesCard")}
          value={opTypes.isLoading ? "…" : String(opTypes.data?.length ?? 0)}
          subtitle={t("dashboard.opTypesSubtitle")}
          icon={<Wrench className="h-5 w-5" />}
          href={isManager ? "/maintenance/operation-types" : undefined}
        />
        <StatCard
          title={t("dashboard.statusCard")}
          value={apiDown ? t("dashboard.statusDown") : t("dashboard.statusUp")}
          subtitle={apiDown ? t("dashboard.statusDownDesc") : t("dashboard.statusUpDesc")}
          icon={<Activity className={`h-5 w-5 ${apiDown ? "text-destructive" : ""}`} />}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("dashboard.byProtocol")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {protocolEntries.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {t("dashboard.byProtocolEmpty")}
              </p>
            ) : (
              <ul className="divide-y text-sm">
                {protocolEntries.map(([proto, n]) => (
                  <li
                    key={proto}
                    className="flex items-center justify-between py-2 first:pt-0 last:pb-0"
                  >
                    <span className="font-medium">{proto}</span>
                    <span className="text-muted-foreground tabular-nums">{n}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("dashboard.quickActions")}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Gate roles={["operator"]}>
              <Link
                href="/devices/new"
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                {t("dashboard.registerDevice")}
              </Link>
            </Gate>
            <Gate roles={["maintenance_manager"]}>
              <Link
                href="/maintenance/operation-types"
                className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent"
              >
                {t("dashboard.manageOpTypes")}
              </Link>
            </Gate>
            <Link
              href="/devices"
              className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent"
            >
              {t("nav.devices")}
            </Link>
          </CardContent>
        </Card>
      </div>

      <RecentMeasurements devices={list} />
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
