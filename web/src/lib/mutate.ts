"use client";

import { useMutation, type UseMutationOptions } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { ApiError } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";

export interface MutateWithToastOptions<T, V>
  extends Omit<
    UseMutationOptions<T, ApiError, V>,
    "mutationFn" | "onSuccess" | "onError"
  > {
  mutationFn: (vars: V) => Promise<T>;
  successKey?: string;
  errorKey?: string;
  onSuccess?: (data: T, vars: V) => void;
  onError?: (err: ApiError, vars: V) => void;
}

export function useMutateWithToast<T, V>(opts: MutateWithToastOptions<T, V>) {
  const t = useTranslations();
  const {
    mutationFn,
    successKey = "toast.saved",
    errorKey = "toast.saveFailed",
    onSuccess,
    onError,
    ...rest
  } = opts;

  return useMutation<T, ApiError, V>({
    ...rest,
    mutationFn,
    onSuccess: (data, vars) => {
      toast({ title: t(successKey) });
      onSuccess?.(data, vars);
    },
    onError: (err, vars) => {
      const isForbidden = err instanceof ApiError && err.status === 403;
      toast({
        title: t(isForbidden ? "toast.forbidden" : errorKey),
        description: err instanceof ApiError ? err.message : String(err),
        variant: "destructive",
      });
      onError?.(err, vars);
    },
  });
}
