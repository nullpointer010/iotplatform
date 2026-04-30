"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DeleteConfirm } from "@/components/delete-confirm";
import { MaintenanceLogForm } from "@/components/forms/maintenance-log-form";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";

export function MaintenanceTab({ deviceId }: { deviceId: string }) {
  const qc = useQueryClient();
  const log = useQuery({
    queryKey: ["maintenance-log", deviceId],
    queryFn: () => api.listMaintenanceLog(deviceId, { page_size: 200 }),
  });
  const opTypes = useQuery({
    queryKey: ["operation-types"],
    queryFn: () => api.listOperationTypes(),
  });
  const opTypeName = (id: string) =>
    opTypes.data?.find((o) => o.id === id)?.name ?? id;

  const del = useMutation({
    mutationFn: (id: string) => api.deleteMaintenanceLog(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["maintenance-log", deviceId] });
      toast({ title: "Log entry removed" });
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : (err as Error).message;
      toast({ title: "Delete failed", description: message, variant: "destructive" });
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Add maintenance entry</CardTitle>
        </CardHeader>
        <CardContent>
          <MaintenanceLogForm deviceId={deviceId} />
        </CardContent>
      </Card>

      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Start</TableHead>
              <TableHead>End</TableHead>
              <TableHead>Operation</TableHead>
              <TableHead>Component</TableHead>
              <TableHead>Notes</TableHead>
              <TableHead className="w-[1%]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {log.isLoading && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            )}
            {log.data?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  No maintenance entries yet.
                </TableCell>
              </TableRow>
            )}
            {log.data?.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="font-mono text-xs">{entry.start_time}</TableCell>
                <TableCell className="font-mono text-xs">
                  {entry.end_time ?? "—"}
                </TableCell>
                <TableCell>{opTypeName(entry.operation_type_id)}</TableCell>
                <TableCell>{entry.component_path ?? "—"}</TableCell>
                <TableCell className="max-w-[24rem] truncate">
                  {entry.details_notes ?? "—"}
                </TableCell>
                <TableCell>
                  <DeleteConfirm
                    title="Remove this maintenance entry?"
                    onConfirm={() => del.mutateAsync(entry.id)}
                    trigger={
                      <Button variant="ghost" size="icon" aria-label="Delete">
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    }
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
