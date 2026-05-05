"use client";

import * as React from "react";
import Link from "next/link";
import { useQueries } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { formatDistanceToNowStrict, parseISO } from "date-fns";
import { es as esLocale, enUS as enLocale } from "date-fns/locale";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Device } from "@/lib/types";

const TOP_N = 5;
const POLL_MS = 30_000;
const MAX_DEVICES = 30;

interface Row {
  device: Device;
  attr: string;
  value: number;
  unit?: string | null;
  iso: string;
}

export function RecentMeasurements({ devices }: { devices: Device[] }) {
  const t = useTranslations();
  const locale = useLocale();
  const dfLocale = locale.startsWith("es") ? esLocale : enLocale;

  // Cap to avoid stampedes; pick devices with a controlledProperty.
  const targets = React.useMemo(
    () =>
      devices
        .filter((d) => (d.controlledProperty?.length ?? 0) > 0)
        .slice(0, MAX_DEVICES),
    [devices],
  );

  const queries = useQueries({
    queries: targets.map((d) => {
      const attr = d.controlledProperty![0];
      return {
        queryKey: ["recent", d.id, attr],
        queryFn: () =>
          api.getTelemetry(d.id, { controlledProperty: attr, lastN: 1 }),
        refetchInterval: POLL_MS,
        staleTime: POLL_MS / 2,
      };
    }),
  });

  const rows: Row[] = [];
  queries.forEach((q, i) => {
    const d = targets[i];
    const e = q.data?.entries?.[0];
    if (!d || !e) return;
    rows.push({
      device: d,
      attr: d.controlledProperty![0],
      value: e.numValue,
      unit: e.unitCode,
      iso: e.dateObserved,
    });
  });
  rows.sort((a, b) => (a.iso < b.iso ? 1 : -1));
  const top = rows.slice(0, TOP_N);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {t("dashboard.recentTitle")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {top.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {t("dashboard.recentEmpty")}
          </p>
        ) : (
          <ul className="divide-y text-sm">
            {top.map((r) => (
              <li
                key={`${r.device.id}-${r.attr}`}
                className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0"
              >
                <div className="min-w-0">
                  <Link
                    href={`/devices/${encodeURIComponent(r.device.id)}`}
                    className="block truncate font-medium hover:underline"
                  >
                    {r.device.name ?? r.device.id}
                  </Link>
                  <p className="truncate text-xs text-muted-foreground">
                    {r.attr}
                  </p>
                </div>
                <div className="text-right">
                  <div className="font-semibold tabular-nums">
                    {Number.isInteger(r.value) ? r.value : r.value.toFixed(2)}
                    {r.unit ? (
                      <span className="ml-1 text-xs font-normal text-muted-foreground">
                        {r.unit}
                      </span>
                    ) : null}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {formatDistanceToNowStrict(parseISO(r.iso), {
                      addSuffix: true,
                      locale: dfLocale,
                    })}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
