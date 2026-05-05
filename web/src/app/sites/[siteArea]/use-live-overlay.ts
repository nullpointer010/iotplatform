"use client";

import * as React from "react";
import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Placement } from "@/lib/types";

export interface LiveEntry {
  value: number;
  unit: string | null;
  iso: string;
}

const POLL_MS = 30_000;

/**
 * Fan-out polling for the latest sample of each placed device's
 * primary controlled property. Polling pauses when the tab is hidden.
 */
export function useLiveOverlay(
  siteArea: string,
  placed: Placement[],
): Map<string, LiveEntry> {
  const queries = useQueries({
    queries: placed.map((p) => {
      const prop = p.primary_property ?? "";
      return {
        queryKey: ["overlay", siteArea, p.device_id, prop],
        queryFn: () =>
          api.getTelemetry(p.device_id, {
            controlledProperty: prop,
            lastN: 1,
          }),
        refetchInterval: POLL_MS,
        refetchIntervalInBackground: false,
        staleTime: POLL_MS / 2,
        enabled: prop.length > 0,
      };
    }),
  });

  // Build a stable signature from each entry's timestamp so the
  // memoized Map only changes when at least one device's last sample
  // moves.
  const signature = queries
    .map((q) => q.data?.entries?.[0]?.dateObserved ?? "")
    .join("|");

  return React.useMemo(() => {
    const map = new Map<string, LiveEntry>();
    queries.forEach((q, i) => {
      const p = placed[i];
      const e = q.data?.entries?.[0];
      if (!p || !e) return;
      if (!Number.isFinite(e.numValue)) return;
      map.set(p.device_id, {
        value: e.numValue,
        unit: e.unitCode ?? null,
        iso: e.dateObserved,
      });
    });
    return map;
    // `queries` is recreated each render; we depend on `signature` to
    // re-derive the map only when the data actually changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [placed, signature]);
}
