"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { formatDistanceToNowStrict, parseISO } from "date-fns";
import { es as esLocale, enUS as enLocale } from "date-fns/locale";
import type { Locale } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { FreshnessBadge } from "@/components/ui/freshness-badge";
import { Sparkline } from "@/components/charts/sparkline";
import { api } from "@/lib/api";
import { freshnessOf } from "@/lib/freshness";
import type { Device, DeviceStateAttribute } from "@/lib/types";

const STATE_POLL_MS = 15_000;
const SPARK_POLL_MS = 60_000;

function isNumberAttr(device: Device, attr: string, raw: unknown): boolean {
  const declared = device.dataTypes?.[attr];
  if (typeof declared === "string") return declared === "Number";
  return typeof raw === "number";
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  if (typeof v === "string" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

export function StateTab({
  deviceId,
  device,
}: {
  deviceId: string;
  device: Device;
}) {
  const t = useTranslations();
  const locale = useLocale();
  const dfLocale = locale.startsWith("es") ? esLocale : enLocale;

  const stateQ = useQuery({
    queryKey: ["state", deviceId],
    queryFn: () => api.getState(deviceId),
    refetchInterval: STATE_POLL_MS,
  });

  const data = stateQ.data;
  const attributes: Record<string, DeviceStateAttribute> = data?.attributes ?? {};
  const attrNames = Object.keys(attributes).sort();

  const lastReportFresh = freshnessOf(
    data?.dateLastValueReported,
    STATE_POLL_MS / 1000,
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {t("state.deviceState")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="font-medium text-muted-foreground">
              {t("state.deviceState")}
            </dt>
            <dd>{data?.deviceState ?? "—"}</dd>
            <dt className="font-medium text-muted-foreground">
              {t("state.lastReport")}
            </dt>
            <dd className="flex items-center gap-2">
              <FreshnessBadge freshness={lastReportFresh} />
              <span className="text-muted-foreground">
                {data?.dateLastValueReported
                  ? formatDistanceToNowStrict(
                      parseISO(data.dateLastValueReported),
                      { addSuffix: true, locale: dfLocale },
                    )
                  : "—"}
              </span>
            </dd>
            {data?.batteryLevel !== undefined && (
              <>
                <dt className="font-medium text-muted-foreground">
                  {t("state.battery")}
                </dt>
                <dd>{Math.round(data.batteryLevel * 100) / 100}</dd>
              </>
            )}
          </dl>
        </CardContent>
      </Card>

      {stateQ.isLoading ? (
        <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
      ) : attrNames.length === 0 ? (
        <EmptyState
          title={t("state.emptyTitle")}
          description={t("state.emptyHint")}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {attrNames.map((attr) => {
            const raw = attributes[attr]?.value;
            const numeric = isNumberAttr(device, attr, raw);
            return (
              <AttrCard
                key={attr}
                attr={attr}
                value={raw}
                numeric={numeric}
                deviceId={deviceId}
                lastSeenIso={data?.dateLastValueReported}
                dfLocale={dfLocale}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function AttrCard({
  attr,
  value,
  numeric,
  deviceId,
  lastSeenIso,
  dfLocale,
}: {
  attr: string;
  value: unknown;
  numeric: boolean;
  deviceId: string;
  lastSeenIso?: string;
  dfLocale: Locale;
}) {
  const t = useTranslations();
  const sparkQ = useQuery({
    queryKey: ["spark", deviceId, attr],
    queryFn: () =>
      api.getTelemetry(deviceId, { controlledProperty: attr, lastN: 60 }),
    enabled: numeric,
    refetchInterval: SPARK_POLL_MS,
  });

  const points = (sparkQ.data?.entries ?? [])
    .map((e) => ({ t: new Date(e.dateObserved).getTime(), v: e.numValue }))
    .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v))
    .sort((a, b) => a.t - b.t);
  const unit = sparkQ.data?.entries?.[0]?.unitCode ?? undefined;

  const last = points[points.length - 1];
  const lastIso = last
    ? new Date(last.t).toISOString()
    : lastSeenIso;
  const fresh = freshnessOf(lastIso, STATE_POLL_MS / 1000);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{attr}</CardTitle>
        <FreshnessBadge freshness={fresh} />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl font-semibold tabular-nums">
            {formatValue(value)}
          </span>
          {unit && (
            <span className="text-sm text-muted-foreground">{unit}</span>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          {lastIso
            ? t("state.updatedAgo", {
                ago: formatDistanceToNowStrict(parseISO(lastIso), {
                  locale: dfLocale,
                }),
              })
            : "—"}
        </p>
        {numeric && (
          <div className="mt-2">
            <Sparkline data={points} />
            <p className="mt-1 text-[10px] text-muted-foreground">
              {t("state.sparklineHint")}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
