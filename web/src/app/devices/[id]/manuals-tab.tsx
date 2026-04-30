"use client";

import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Trash2, FileText, Upload } from "lucide-react";
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
import { Gate } from "@/components/gate";
import { api } from "@/lib/api";
import { useMutateWithToast } from "@/lib/mutate";
import type { DeviceManual } from "@/lib/types";

const MAX_BYTES = 10 * 1024 * 1024;

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
}

export function ManualsTab({ deviceId }: { deviceId: string }) {
  const qc = useQueryClient();
  const t = useTranslations();
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [pending, setPending] = useState<File | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);

  const list = useQuery({
    queryKey: ["manuals", deviceId],
    queryFn: () => api.listManuals(deviceId),
  });

  const upload = useMutateWithToast<DeviceManual, File>({
    mutationFn: (file) => api.uploadManual(deviceId, file),
    successKey: "toast.created",
    errorKey: "manuals.uploadFailed",
    onSuccess: () => {
      setPending(null);
      if (fileInput.current) fileInput.current.value = "";
      qc.invalidateQueries({ queryKey: ["manuals", deviceId] });
    },
  });

  const del = useMutateWithToast<void, string>({
    mutationFn: (id) => api.deleteManual(id),
    successKey: "toast.deleted",
    errorKey: "toast.deleteFailed",
    onSuccess: () => qc.invalidateQueries({ queryKey: ["manuals", deviceId] }),
  });

  const onPick = (file: File | null) => {
    setClientError(null);
    if (!file) {
      setPending(null);
      return;
    }
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setClientError(t("manuals.notPdf"));
      setPending(null);
      return;
    }
    if (file.size > MAX_BYTES) {
      setClientError(t("manuals.tooLarge"));
      setPending(null);
      return;
    }
    setPending(file);
  };

  const onSubmit = () => {
    if (pending) upload.mutate(pending);
  };

  const isEmpty = !list.isLoading && (list.data?.length ?? 0) === 0;

  return (
    <div className="space-y-4">
      <Gate roles={["operator", "maintenance_manager"]}>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("manuals.addTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-3">
            <input
              ref={fileInput}
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => onPick(e.target.files?.[0] ?? null)}
              className="block text-sm"
            />
            <Button
              type="button"
              onClick={onSubmit}
              disabled={!pending || upload.isPending}
            >
              <Upload className="mr-2 h-4 w-4" />
              {upload.isPending ? t("manuals.uploading") : t("manuals.uploadButton")}
            </Button>
            {clientError ? (
              <p className="text-sm text-destructive">{clientError}</p>
            ) : null}
          </CardContent>
        </Card>
      </Gate>

      {isEmpty ? (
        <EmptyState
          title={t("manuals.emptyTitle")}
          description={t("manuals.emptyHint")}
        />
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("manuals.field.filename.label")}</TableHead>
                <TableHead>{t("manuals.field.size.label")}</TableHead>
                <TableHead>{t("manuals.field.uploadedAt.label")}</TableHead>
                <TableHead>{t("manuals.field.uploadedBy.label")}</TableHead>
                <TableHead className="w-[1%]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.isLoading && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    {t("common.loading")}
                  </TableCell>
                </TableRow>
              )}
              {list.data?.map((m) => (
                <TableRow key={m.id}>
                  <TableCell>
                    <a
                      href={api.manualUrl(m.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 text-primary hover:underline"
                    >
                      <FileText className="h-4 w-4" />
                      {m.filename}
                    </a>
                  </TableCell>
                  <TableCell>{formatSize(m.size_bytes)}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {m.uploaded_at}
                  </TableCell>
                  <TableCell>{m.uploaded_by ?? "—"}</TableCell>
                  <TableCell>
                    <Gate roles={[]}>
                      <DeleteConfirm
                        title={t("manuals.deleteConfirmTitle")}
                        description={t("manuals.deleteConfirmDesc")}
                        onConfirm={() => del.mutateAsync(m.id)}
                        trigger={
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={t("common.delete")}
                          >
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

// Re-export so unit tests can import the helper if needed.
export const __test = { formatSize, MAX_BYTES };
