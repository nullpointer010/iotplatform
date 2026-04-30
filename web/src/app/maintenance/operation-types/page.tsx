"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
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
import { OperationTypeForm } from "@/components/forms/operation-type-form";
import { api } from "@/lib/api";
import { useMe, useHasRole } from "@/lib/auth";
import { useMutateWithToast } from "@/lib/mutate";
import { optimisticListDelete } from "@/lib/optimistic";
import type { OperationType } from "@/lib/types";

export default function OperationTypesPage() {
  const qc = useQueryClient();
  const t = useTranslations();
  const router = useRouter();
  const me = useMe();
  const allowed = useHasRole("maintenance_manager");
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<OperationType | null>(null);

  React.useEffect(() => {
    if (me.isSuccess && !allowed) {
      router.replace("/devices");
    }
  }, [me.isSuccess, allowed, router]);

  const list = useQuery({
    queryKey: ["operation-types"],
    queryFn: () => api.listOperationTypes(),
  });

  const del = useMutateWithToast<void, string>({
    mutationFn: async (id) => {
      const { rollback } = optimisticListDelete<OperationType>(
        qc,
        ["operation-types"],
        (o) => o.id === id,
      );
      try {
        await api.deleteOperationType(id);
      } catch (e) {
        rollback();
        throw e;
      }
    },
    successKey: "toast.deleted",
    errorKey: "toast.deleteFailed",
    onSuccess: () => qc.invalidateQueries({ queryKey: ["operation-types"] }),
  });

  const isEmpty = !list.isLoading && (list.data?.length ?? 0) === 0;

  if (!allowed) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("opType.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("opType.subtitle")}</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" /> {t("opType.new")}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t("opType.new")}</DialogTitle>
            </DialogHeader>
            <OperationTypeForm onDone={() => setCreateOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      {isEmpty ? (
        <EmptyState
          title={t("opType.emptyTitle")}
          description={t("opType.emptyHint")}
          action={
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" /> {t("opType.new")}
            </Button>
          }
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("opType.title")}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("opType.field.name.label")}</TableHead>
                  <TableHead>{t("opType.field.description.label")}</TableHead>
                  <TableHead>{t("opType.field.requiresComponent.label")}</TableHead>
                  <TableHead className="w-[1%]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.isLoading && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground">
                      {t("common.loading")}
                    </TableCell>
                  </TableRow>
                )}
                {list.data?.map((o) => (
                  <TableRow key={o.id}>
                    <TableCell className="font-medium">{o.name}</TableCell>
                    <TableCell className="max-w-[32rem] truncate">
                      {o.description ?? "—"}
                    </TableCell>
                    <TableCell>
                      {o.requires_component ? (
                        <Badge variant="warning">{t("common.yes")}</Badge>
                      ) : (
                        <Badge variant="secondary">{t("common.no")}</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setEditing(o)}
                          aria-label={t("common.edit")}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <DeleteConfirm
                          title={t("opType.deleteConfirmTitle")}
                          description={t("opType.deleteConfirmDesc")}
                          onConfirm={() => del.mutateAsync(o.id)}
                          trigger={
                            <Button variant="ghost" size="icon" aria-label={t("common.delete")}>
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
          </CardContent>
        </Card>
      )}

      <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("common.edit")}</DialogTitle>
          </DialogHeader>
          {editing && (
            <OperationTypeForm initial={editing} onDone={() => setEditing(null)} />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
