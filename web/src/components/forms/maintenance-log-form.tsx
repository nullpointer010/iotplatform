"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import {
  maintenanceLogFormSchema,
  type MaintenanceLogFormValues,
} from "@/lib/zod";
import { toast } from "@/components/ui/use-toast";

type Props = { deviceId: string };

export function MaintenanceLogForm({ deviceId }: Props) {
  const qc = useQueryClient();
  const opTypes = useQuery({
    queryKey: ["operation-types"],
    queryFn: () => api.listOperationTypes(),
  });
  const form = useForm<MaintenanceLogFormValues>({
    resolver: zodResolver(maintenanceLogFormSchema),
    defaultValues: { start_time: new Date().toISOString().slice(0, 16) },
  });

  const mutation = useMutation({
    mutationFn: async (values: MaintenanceLogFormValues) => {
      const body = {
        ...values,
        start_time: new Date(values.start_time).toISOString(),
        end_time: values.end_time
          ? new Date(values.end_time).toISOString()
          : undefined,
      };
      return api.createMaintenanceLog(deviceId, body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["maintenance-log", deviceId] });
      toast({ title: "Log entry created" });
      form.reset({ start_time: new Date().toISOString().slice(0, 16) });
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : (err as Error).message;
      toast({ title: "Save failed", description: message, variant: "destructive" });
    },
  });

  return (
    <form
      className="grid gap-4 md:grid-cols-2"
      onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
    >
      <div className="space-y-1.5 md:col-span-2">
        <Label>Operation type *</Label>
        <Select
          value={form.watch("operation_type_id") ?? ""}
          onValueChange={(v) => form.setValue("operation_type_id", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder={opTypes.isLoading ? "Loading…" : "Pick"} />
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
        <Label>Start *</Label>
        <Input type="datetime-local" {...form.register("start_time")} />
      </div>
      <div className="space-y-1.5">
        <Label>End</Label>
        <Input type="datetime-local" {...form.register("end_time")} />
        {form.formState.errors.end_time && (
          <p className="text-xs text-destructive">
            {form.formState.errors.end_time.message}
          </p>
        )}
      </div>
      <div className="space-y-1.5">
        <Label>Component path</Label>
        <Input
          placeholder="e.g. cooling.fan.bearing"
          {...form.register("component_path")}
        />
      </div>
      <div className="space-y-1.5">
        <Label>Performed by (UUID)</Label>
        <Input {...form.register("performed_by_id")} />
      </div>
      <div className="space-y-1.5 md:col-span-2">
        <Label>Notes</Label>
        <Textarea {...form.register("details_notes")} />
      </div>
      <div className="md:col-span-2 flex justify-end">
        <Button type="submit" loading={mutation.isPending}>
          Add entry
        </Button>
      </div>
    </form>
  );
}
