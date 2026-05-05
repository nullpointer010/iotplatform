"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { DateTimeInput } from "@/components/ui/datetime-input";
import { TimeSeriesChart, type TimeSeriesRange } from "@/components/charts/time-series-chart";
import { api } from "@/lib/api";
import { paginate, PAGE_SIZE } from "@/lib/paginate";
import { cn } from "@/lib/utils";
import type { Device } from "@/lib/types";

const RANGES: { key: Exclude<TimeSeriesRange, "custom">; ms: number }[] = [
  { key: "24h", ms: 24 * 3600 * 1000 },
  { key: "7d", ms: 7 * 24 * 3600 * 1000 },
  { key: "30d", ms: 30 * 24 * 3600 * 1000 },
];

function isoMs(ms: number): string {
  return new Date(ms).toISOString();
}

function rangeWindow(
  range: TimeSeriesRange,
  customFrom: string | null,
  customTo: string | null,
): { fromDate?: string; toDate?: string } {
  if (range === "custom") {
    return {
      fromDate: customFrom ?? undefined,
      toDate: customTo ?? undefined,
    };
  }
  const ms = RANGES.find((r) => r.key === range)?.ms ?? 24 * 3600 * 1000;
  const now = Date.now();
  return { fromDate: isoMs(now - ms), toDate: isoMs(now) };
}

export function buildCsv(
  entries: { dateObserved: string; numValue: number; unitCode?: string | null }[],
): string {
  const rows = ["dateObserved,localTime,numValue,unitCode"];
  for (const e of entries) {
    const local = format(new Date(e.dateObserved), "yyyy-MM-dd HH:mm:ss");
    rows.push(
      `${e.dateObserved},${local},${e.numValue},${e.unitCode ?? ""}`,
    );
  }
  return rows.join("\n");
}

function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function safeFilenamePart(s: string): string {
  return s.replace(/[^a-zA-Z0-9_.-]+/g, "_");
}

function rangeLabel(
  t: (key: string) => string,
  r: TimeSeriesRange,
): string {
  switch (r) {
    case "24h":
      return t("telemetry.range.24h");
    case "7d":
      return t("telemetry.range.7d");
    case "30d":
      return t("telemetry.range.30d");
    case "custom":
      return t("telemetry.range.custom");
  }
}

export function TelemetryTab({
  deviceId,
  device,
}: {
  deviceId: string;
  device: Device;
}) {
  const t = useTranslations();
  const properties = device.controlledProperty ?? [];
  const [selected, setSelected] = React.useState<string>(properties[0] ?? "");
  const [custom, setCustom] = React.useState<string>("");
  const [range, setRange] = React.useState<TimeSeriesRange>("24h");
  const [customFrom, setCustomFrom] = React.useState<string | null>(null);
  const [customTo, setCustomTo] = React.useState<string | null>(null);
  const [tablePage, setTablePage] = React.useState<number>(1);

  const cp = selected || custom;
  // Reset table pagination whenever the dataset changes.
  React.useEffect(() => {
    setTablePage(1);
  }, [cp, range, customFrom, customTo]);
  // Memoize so the queryKey is stable across renders. `rangeWindow`
  // calls Date.now() for the non-custom ranges; without memoization
  // the key changes every render and react-query keeps refetching
  // (the tab gets stuck on "Cargando…").
  const window = React.useMemo(
    () => rangeWindow(range, customFrom, customTo),
    [range, customFrom, customTo],
  );

  const tele = useQuery({
    queryKey: ["telemetry", deviceId, cp, range, window.fromDate, window.toDate],
    queryFn: () =>
      api.getTelemetry(deviceId, {
        controlledProperty: cp,
        fromDate: window.fromDate,
        toDate: window.toDate,
        lastN: 1000,
      }),
    enabled: cp.length > 0,
  });

  const entries = tele.data?.entries ?? [];
  const points = entries
    .map((e) => ({ t: new Date(e.dateObserved).getTime(), v: e.numValue }))
    .filter((p) => Number.isFinite(p.t) && Number.isFinite(p.v))
    .sort((a, b) => a.t - b.t);
  const unit = entries[0]?.unitCode ?? null;

  const onExport = () => {
    if (!entries.length) return;
    const from = window.fromDate ?? "all";
    const to = window.toDate ?? "now";
    const name = `${safeFilenamePart(deviceId)}_${safeFilenamePart(cp)}_${from}_${to}.csv`;
    downloadCsv(name, buildCsv(entries));
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("device.tab.telemetry")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-1.5">
              <Label>{t("device.field.controlledProperty.label")}</Label>
              {properties.length > 0 ? (
                <Select
                  value={selected}
                  onValueChange={(v) => {
                    setSelected(v);
                    setCustom("");
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {properties.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  value={custom}
                  onChange={(e) => setCustom(e.target.value)}
                  placeholder="temperature"
                />
              )}
            </div>
            <div className="md:col-span-2 flex flex-wrap items-end gap-2">
              {(["24h", "7d", "30d", "custom"] as TimeSeriesRange[]).map((r) => (
                <Button
                  key={r}
                  type="button"
                  variant={range === r ? "default" : "outline"}
                  size="sm"
                  onClick={() => setRange(r)}
                >
                  {rangeLabel(t, r)}
                </Button>
              ))}
              <div className="ml-auto">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={onExport}
                  disabled={!entries.length}
                >
                  {t("telemetry.exportCsv")}
                </Button>
              </div>
            </div>
          </div>
          {range === "custom" && (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label>{t("telemetry.from")}</Label>
                <DateTimeInput value={customFrom} onChange={setCustomFrom} />
              </div>
              <div className="space-y-1.5">
                <Label>{t("telemetry.to")}</Label>
                <DateTimeInput value={customTo} onChange={setCustomTo} />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {!cp ? (
        <EmptyState
          title={t("telemetry.emptyTitle")}
          description={t("telemetry.emptyHint")}
        />
      ) : tele.isError ? (
        <div className="rounded-lg border bg-card p-6 text-center text-destructive">
          {(tele.error as Error).message}
        </div>
      ) : tele.isLoading ? (
        <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
      ) : points.length === 0 ? (
        <EmptyState
          title={t("telemetry.emptyTitle")}
          description={t("telemetry.emptyHint")}
        />
      ) : (
        <Card>
          <CardContent className={cn("pt-6")}>
            <TimeSeriesChart data={points} range={range} unit={unit} />
          </CardContent>
        </Card>
      )}

      {entries.length > 0 && (
        <details className="rounded-lg border bg-card">
          <summary className="cursor-pointer px-4 py-2 text-sm font-medium">
            {t("telemetry.rawTable")}
          </summary>
          {(() => {
            const sorted = [...entries].sort((a, b) =>
              b.dateObserved.localeCompare(a.dateObserved),
            );
            const page = paginate(sorted, tablePage, PAGE_SIZE);
            return (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>Value</TableHead>
                      <TableHead>Unit</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {page.items.map((e, i) => (
                      <TableRow key={`${e.dateObserved}-${i}`}>
                        <TableCell
                          className="font-mono text-xs"
                          title={e.dateObserved}
                        >
                          {format(new Date(e.dateObserved), "yyyy-MM-dd HH:mm:ss")}
                        </TableCell>
                        <TableCell>{e.numValue}</TableCell>
                        <TableCell>{e.unitCode ?? "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <div className="flex items-center justify-between gap-2 px-4 py-2 text-sm">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setTablePage((p) => p - 1)}
                    disabled={page.page <= 1}
                  >
                    {t("telemetry.table.prev")}
                  </Button>
                  <span className="text-muted-foreground">
                    {t("telemetry.table.pageOf", {
                      page: page.page,
                      total: page.totalPages,
                    })}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setTablePage((p) => p + 1)}
                    disabled={page.page >= page.totalPages}
                  >
                    {t("telemetry.table.next")}
                  </Button>
                </div>
              </>
            );
          })()}
        </details>
      )}
    </div>
  );
}
