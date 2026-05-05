"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FieldLabel } from "@/components/forms/field-label";
import { api } from "@/lib/api";
import { useMutateWithToast } from "@/lib/mutate";
import {
  maintenanceLogFormSchema,
  type MaintenanceLogFormValues,
} from "@/lib/zod";

type Props = { deviceId: string };

export function MaintenanceLogForm({ deviceId }: Props) {
  const qc = useQueryClient();
  const t = useTranslations();
  const opTypes = useQuery({
    queryKey: ["operation-types"],
    queryFn: () => api.listOperationTypes(),
  });
  const form = useForm<MaintenanceLogFormValues>({
    resolver: zodResolver(maintenanceLogFormSchema),
    mode: "onBlur",
    defaultValues: { start_time: new Date().toISOString().slice(0, 16) },
  });

  const mutation = useMutateWithToast({
    mutationFn: async (values: MaintenanceLogFormValues) => {
      const body = {
        ...values,
        start_time: new Date(values.start_time).toISOString(),
        end_time: values.end_time ? new Date(values.end_time).toISOString() : undefined,
      };
      return api.createMaintenanceLog(deviceId, body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["maintenance-log", deviceId] });
      form.reset({ start_time: new Date().toISOString().slice(0, 16) });
    },
    successKey: "toast.created",
  });

  return (
    <form
      className="grid gap-4 md:grid-cols-2"
      onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
    >
      <div className="space-y-1.5 md:col-span-2">
        <FieldLabel
          htmlFor="ml-op"
          label={t("maintLog.field.operationType.label")}
          required
        />
        <Select
          value={form.watch("operation_type_id") ?? ""}
          onValueChange={(v) => form.setValue("operation_type_id", v)}
        >
          <SelectTrigger id="ml-op">
            <SelectValue placeholder={opTypes.isLoading ? t("common.loading") : "—"} />
          </SelectTrigger>
          <SelectContent>
            {(opTypes.data ?? []).map((o) => (
              <SelectItem key={o.id} value={o.id}>
                {o.name}
                {o.requires_component ? " (component required)" : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {form.formState.errors.operation_type_id && (
          <p className="text-xs text-destructive">
            {form.formState.errors.operation_type_id.message}
          </p>
        )}
      </div>
      <div className="space-y-1.5">
        <FieldLabel
          htmlFor="ml-start"
          label={t("maintLog.field.startTime.label")}
          required
        />
        <Input
          id="ml-start"
          type="datetime-local"
          lang="es-ES"
          aria-invalid={form.formState.errors.start_time ? true : undefined}
          {...form.register("start_time")}
        />
      </div>
      <div className="space-y-1.5">
        <FieldLabel
          htmlFor="ml-end"
          label={t("maintLog.field.endTime.label")}
          tooltip={t("maintLog.field.endTime.tooltip")}
        />
        <Input
          id="ml-end"
          type="datetime-local"
          lang="es-ES"
          aria-invalid={form.formState.errors.end_time ? true : undefined}
          {...form.register("end_time")}
        />
        {form.formState.errors.end_time && (
          <p className="text-xs text-destructive">
            {form.formState.errors.end_time.message}
          </p>
        )}
      </div>
      <div className="space-y-1.5">
        <FieldLabel
          htmlFor="ml-comp"
          label={t("maintLog.field.componentPath.label")}
          tooltip={t("maintLog.field.componentPath.tooltip")}
        />
        <Input id="ml-comp" placeholder={t("maintLog.placeholder.componentPath")} {...form.register("component_path")} />
      </div>
      <div className="space-y-1.5">
        <FieldLabel
          htmlFor="ml-perf"
          label={t("maintLog.field.performedBy.label")}
          tooltip={t("maintLog.field.performedBy.tooltip")}
        />
        <Input id="ml-perf" placeholder={t("maintLog.placeholder.performedBy")} {...form.register("performed_by_id")} />
      </div>
      <div className="space-y-1.5 md:col-span-2">
        <FieldLabel htmlFor="ml-notes" label={t("maintLog.field.detailsNotes.label")} />
        <Textarea id="ml-notes" placeholder={t("maintLog.placeholder.detailsNotes")} {...form.register("details_notes")} />
      </div>
      <div className="md:col-span-2 flex justify-end">
        <Button type="submit" loading={mutation.isPending}>
          {t("maintLog.addTitle")}
        </Button>
      </div>
    </form>
  );
}
