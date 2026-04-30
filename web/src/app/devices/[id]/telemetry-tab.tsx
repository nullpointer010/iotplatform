"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
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
import { api } from "@/lib/api";
import type { Device } from "@/lib/types";

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
  const [lastN, setLastN] = React.useState<number>(50);

  const cp = selected || custom;

  const tele = useQuery({
    queryKey: ["telemetry", deviceId, cp, lastN],
    queryFn: () => api.getTelemetry(deviceId, { controlledProperty: cp, lastN }),
    enabled: cp.length > 0,
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("device.tab.telemetry")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
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
          <div className="space-y-1.5">
            <Label>Last N</Label>
            <Input
              type="number"
              min={1}
              max={1000}
              value={lastN}
              onChange={(e) => setLastN(Number(e.target.value) || 50)}
            />
          </div>
          <div className="flex items-end">
            <Button onClick={() => tele.refetch()} disabled={!cp}>
              {t("common.search")}
            </Button>
          </div>
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
      ) : tele.data?.entries.length === 0 ? (
        <EmptyState
          title={t("telemetry.emptyTitle")}
          description={t("telemetry.emptyHint")}
        />
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Unit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tele.isLoading && (
                <TableRow>
                  <TableCell colSpan={3} className="text-center text-muted-foreground">
                    {t("common.loading")}
                  </TableCell>
                </TableRow>
              )}
              {tele.data?.entries.map((e, i) => (
                <TableRow key={`${e.dateObserved}-${i}`}>
                  <TableCell className="font-mono text-xs">{e.dateObserved}</TableCell>
                  <TableCell>{e.numValue}</TableCell>
                  <TableCell>{e.unitCode ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
