"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";
import { operationTypeFormSchema, type OperationTypeFormValues } from "@/lib/zod";
import { toast } from "@/components/ui/use-toast";
import type { OperationType } from "@/lib/types";

type Props = {
  initial?: OperationType;
  onDone?: () => void;
};

export function OperationTypeForm({ initial, onDone }: Props) {
  const qc = useQueryClient();
  const form = useForm<OperationTypeFormValues>({
    resolver: zodResolver(operationTypeFormSchema),
    defaultValues: {
      name: initial?.name ?? "",
      description: initial?.description ?? "",
      requires_component: initial?.requires_component ?? false,
    },
  });

  const mutation = useMutation({
    mutationFn: async (values: OperationTypeFormValues) => {
      if (initial) return api.updateOperationType(initial.id, values);
      return api.createOperationType(values);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operation-types"] });
      toast({ title: initial ? "Operation type updated" : "Operation type created" });
      form.reset();
      onDone?.();
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : (err as Error).message;
      toast({ title: "Save failed", description: message, variant: "destructive" });
    },
  });

  return (
    <form
      className="space-y-4"
      onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
    >
      <div className="space-y-1.5">
        <Label>Name *</Label>
        <Input {...form.register("name")} />
        {form.formState.errors.name && (
          <p className="text-xs text-destructive">
            {form.formState.errors.name.message}
          </p>
        )}
      </div>
      <div className="space-y-1.5">
        <Label>Description</Label>
        <Textarea {...form.register("description")} />
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" {...form.register("requires_component")} />
        Requires component path
      </label>
      <div className="flex justify-end gap-2">
        <Button type="submit" loading={mutation.isPending}>
          {initial ? "Save" : "Create"}
        </Button>
      </div>
    </form>
  );
}
