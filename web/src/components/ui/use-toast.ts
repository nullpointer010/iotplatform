"use client";

import * as React from "react";

type ToastInput = {
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
  duration?: number;
};

type ToastItem = ToastInput & { id: number };

type Listener = (items: ToastItem[]) => void;

let counter = 0;
let items: ToastItem[] = [];
const listeners = new Set<Listener>();

function emit() {
  for (const l of listeners) l(items);
}

export function toast(input: ToastInput) {
  const id = ++counter;
  items = [...items, { ...input, id }];
  emit();
  setTimeout(() => {
    items = items.filter((t) => t.id !== id);
    emit();
  }, input.duration ?? 4000);
}

export function useToasts(): ToastItem[] {
  const [state, setState] = React.useState<ToastItem[]>(items);
  React.useEffect(() => {
    const listener: Listener = (next) => setState(next);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);
  return state;
}

export function dismissToast(id: number) {
  items = items.filter((t) => t.id !== id);
  emit();
}
