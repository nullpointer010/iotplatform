"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { MapPin } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { api } from "@/lib/api";

export default function SitesPage() {
  const t = useTranslations("sites");
  const sites = useQuery({ queryKey: ["sites"], queryFn: () => api.listSites() });

  return (
    <div className="container space-y-6 py-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </header>
      {sites.isLoading ? (
        <p className="text-sm text-muted-foreground">…</p>
      ) : sites.data && sites.data.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sites.data.map((s) => (
            <li key={s.site_area}>
              <Link
                href={`/sites/${encodeURIComponent(s.site_area)}`}
                className="flex h-full flex-col gap-2 rounded-lg border bg-card p-4 transition-colors hover:bg-accent"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <MapPin className="size-4 text-muted-foreground" aria-hidden />
                    <span className="font-medium">{s.site_area}</span>
                  </div>
                  <Badge variant={s.has_floorplan ? "success" : "secondary"}>
                    {s.has_floorplan ? t("hasPlan") : t("noPlan")}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  {t("deviceCount", { count: s.device_count })}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
      )}
    </div>
  );
}
