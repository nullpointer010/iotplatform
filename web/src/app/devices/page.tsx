"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, Pencil, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DeleteConfirm } from "@/components/delete-confirm";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";
import type { DeviceState } from "@/lib/types";

const stateVariant: Record<DeviceState, "success" | "warning" | "secondary"> = {
  active: "success",
  maintenance: "warning",
  inactive: "secondary",
};

export default function DevicesPage() {
  const qc = useQueryClient();
  const devices = useQuery({
    queryKey: ["devices"],
    queryFn: () => api.listDevices(1000, 0),
  });
  const del = useMutation({
    mutationFn: (id: string) => api.deleteDevice(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["devices"] });
      toast({ title: "Device deleted" });
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : (err as Error).message;
      toast({ title: "Delete failed", description: message, variant: "destructive" });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Devices</h1>
          <p className="text-sm text-muted-foreground">
            All NGSI Device entities registered in Orion.
          </p>
        </div>
        <Button asChild>
          <Link href="/devices/new">
            <Plus className="mr-2 h-4 w-4" /> New device
          </Link>
        </Button>
      </div>

      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Protocol</TableHead>
              <TableHead>State</TableHead>
              <TableHead className="w-[1%]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {devices.isLoading && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {devices.isError && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-destructive">
                  Failed to load devices.
                </TableCell>
              </TableRow>
            )}
            {devices.data?.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No devices yet.
                </TableCell>
              </TableRow>
            )}
            {devices.data?.map((d) => (
              <TableRow key={d.id}>
                <TableCell className="font-medium">
                  <Link
                    href={`/devices/${encodeURIComponent(d.id)}`}
                    className="hover:underline"
                  >
                    {d.name ?? d.id}
                  </Link>
                  <div className="text-xs text-muted-foreground">{d.id}</div>
                </TableCell>
                <TableCell>{d.category ?? "—"}</TableCell>
                <TableCell>{d.supportedProtocol ?? "—"}</TableCell>
                <TableCell>
                  {d.deviceState ? (
                    <Badge variant={stateVariant[d.deviceState]}>{d.deviceState}</Badge>
                  ) : (
                    "—"
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-1">
                    <Button asChild variant="ghost" size="icon" aria-label="View">
                      <Link href={`/devices/${encodeURIComponent(d.id)}`}>
                        <Eye className="h-4 w-4" />
                      </Link>
                    </Button>
                    <Button asChild variant="ghost" size="icon" aria-label="Edit">
                      <Link href={`/devices/${encodeURIComponent(d.id)}/edit`}>
                        <Pencil className="h-4 w-4" />
                      </Link>
                    </Button>
                    <DeleteConfirm
                      title={`Delete ${d.name ?? d.id}?`}
                      description="This permanently removes the device entity from Orion and any maintenance log entries."
                      onConfirm={() => del.mutateAsync(d.id)}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label="Delete">
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      }
                    />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
