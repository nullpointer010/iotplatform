"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FieldLabel } from "@/components/forms/field-label";
import { api } from "@/lib/api";
import { useMutateWithToast } from "@/lib/mutate";
import { operationTypeFormSchema, type OperationTypeFormValues } from "@/lib/zod";
import type { OperationType } from "@/lib/types";

type Props = {
  initial?: OperationType;
  onDone?: () => void;
};

export function OperationTypeForm({ initial, onDone }: Props) {
  const qc = useQueryClient();
  const t = useTranslations();
  const form = useForm<OperationTypeFormValues>({
    resolver: zodResolver(operationTypeFormSchema),
    mode: "onBlur",
    defaultValues: {
      name: initial?.name ?? "",
      description: initial?.description ?? "",
      requires_component: initial?.requires_component ?? false,
    },
  });

  const fmt = (msg?: string): string | undefined => {
    if (!msg) return undefined;
    if (msg.startsWith("orionForbidden:")) {
      return t("zod.orionForbidden", { char: msg.slice("orionForbidden:".length) });
    }
    return msg;
  };

  const mutation = useMutateWithToast<OperationType, OperationTypeFormValues>({
    mutationFn: async (values) =>
      initial
        ? api.updateOperationType(initial.id, values)
        : api.createOperationType(values),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operation-types"] });
      form.reset();
      onDone?.();
    },
  });

  return (
    <form
      className="space-y-4"
      onSubmit={form.handleSubmit((v) => mutation.mutate(v))}
    >
      <div className="space-y-1.5">
        <FieldLabel
          htmlFor="opt-name"
          label={t("opType.field.name.label")}
          tooltip={t("opType.field.name.tooltip")}
          required
        />
        <Input
          id="opt-name"
          placeholder={t("opType.placeholder.name")}
          aria-invalid={form.formState.errors.name ? true : undefined}
          {...form.register("name")}
        />
        {form.formState.errors.name && (
          <p className="text-xs text-destructive">
            {fmt(form.formState.errors.name.message)}
          </p>
        )}
      </div>
      <div className="space-y-1.5">
        <FieldLabel htmlFor="opt-desc" label={t("opType.field.description.label")} />
        <Textarea id="opt-desc" {...form.register("description")} />
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" {...form.register("requires_component")} />
        {t("opType.field.requiresComponent.label")}
      </label>
      <div className="flex justify-end gap-2">
        <Button type="submit" loading={mutation.isPending}>
          {initial ? t("common.save") : t("opType.new")}
        </Button>
      </div>
    </form>
  );
}
