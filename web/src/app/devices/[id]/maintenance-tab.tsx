"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
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
import { EmptyState } from "@/components/ui/empty-state";
import { MaintenanceLogForm } from "@/components/forms/maintenance-log-form";
import { Gate } from "@/components/gate";
import { api } from "@/lib/api";
import { useMutateWithToast } from "@/lib/mutate";
import { optimisticListDelete } from "@/lib/optimistic";
import type { MaintenanceLog } from "@/lib/types";

export function MaintenanceTab({ deviceId }: { deviceId: string }) {
  const qc = useQueryClient();
  const t = useTranslations();
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

  const del = useMutateWithToast<void, string>({
    mutationFn: async (id) => {
      const { rollback } = optimisticListDelete<MaintenanceLog>(
        qc,
        ["maintenance-log", deviceId],
        (e) => e.id === id,
      );
      try {
        await api.deleteMaintenanceLog(id);
      } catch (e) {
        rollback();
        throw e;
      }
    },
    successKey: "toast.deleted",
    errorKey: "toast.deleteFailed",
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["maintenance-log", deviceId] }),
  });

  const isEmpty = !log.isLoading && (log.data?.length ?? 0) === 0;

  return (
    <div className="space-y-4">
      <Gate roles={["operator", "maintenance_manager"]}>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("maintLog.addTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <MaintenanceLogForm deviceId={deviceId} />
          </CardContent>
        </Card>
      </Gate>

      {isEmpty ? (
        <EmptyState
          title={t("maintLog.emptyTitle")}
          description={t("maintLog.emptyHint")}
        />
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("maintLog.field.startTime.label")}</TableHead>
                <TableHead>{t("maintLog.field.endTime.label")}</TableHead>
                <TableHead>{t("maintLog.field.operationType.label")}</TableHead>
                <TableHead>{t("maintLog.field.componentPath.label")}</TableHead>
                <TableHead>{t("maintLog.field.detailsNotes.label")}</TableHead>
                <TableHead className="w-[1%]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {log.isLoading && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    {t("common.loading")}
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
                    <Gate roles={["maintenance_manager"]}>
                      <DeleteConfirm
                        title={t("maintLog.deleteConfirmTitle")}
                        description={t("maintLog.deleteConfirmDesc")}
                        onConfirm={() => del.mutateAsync(entry.id)}
                        trigger={
                          <Button variant="ghost" size="icon" aria-label={t("common.delete")}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        }
                      />
                    </Gate>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
