"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
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
import { api } from "@/lib/api";
import type { Device } from "@/lib/types";

export function TelemetryTab({
  deviceId,
  device,
}: {
  deviceId: string;
  device: Device;
}) {
  const properties = device.controlledProperty ?? [];
  const [selected, setSelected] = React.useState<string>(properties[0] ?? "");
  const [custom, setCustom] = React.useState<string>("");
  const [lastN, setLastN] = React.useState<number>(50);

  const cp = selected || custom;

  const tele = useQuery({
    queryKey: ["telemetry", deviceId, cp, lastN],
    queryFn: () =>
      api.getTelemetry(deviceId, { controlledProperty: cp, lastN }),
    enabled: cp.length > 0,
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Query</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Controlled property</Label>
            {properties.length > 0 ? (
              <Select
                value={selected}
                onValueChange={(v) => {
                  setSelected(v);
                  setCustom("");
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Pick one" />
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
                placeholder="e.g. temperature"
              />
            )}
          </div>
          <div className="space-y-1.5">
            <Label>Last N points</Label>
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
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

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
            {!cp && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">
                  Pick a controlled property to query telemetry.
                </TableCell>
              </TableRow>
            )}
            {tele.isLoading && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {tele.isError && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-destructive">
                  {(tele.error as Error).message}
                </TableCell>
              </TableRow>
            )}
            {tele.data?.entries.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">
                  No measurements in range.
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
    </div>
  );
}
