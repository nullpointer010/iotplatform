"use client";

import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { formatDistanceToNowStrict, parseISO } from "date-fns";
import { es as esLocale, enUS as enLocale } from "date-fns/locale";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { classifyMarker, type MarkerState } from "@/lib/marker-state";
import type { Placement } from "@/lib/types";
import type { LiveEntry } from "./use-live-overlay";

const STATE_CLS: Record<MarkerState, string> = {
  "fresh-active":
    "bg-emerald-500 text-white border-background",
  "fresh-maintenance":
    "bg-amber-500 text-white border-background",
  inactive:
    "bg-muted text-muted-foreground border-background",
  stale:
    "bg-emerald-200/40 text-emerald-900 border-dashed border-emerald-700/50 dark:text-emerald-200",
  "no-data":
    "bg-muted/40 text-muted-foreground border-dashed border-muted-foreground/40",
};

function formatValue(v: number): string {
  return Number.isInteger(v) ? String(v) : v.toFixed(2);
}

interface Props {
  placement: Placement & { x_pct: number; y_pct: number };
  live: LiveEntry | undefined;
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent) => void;
  onDragEnd?: (e: React.DragEvent) => void;
}

export function LiveMarker({
  placement,
  live,
  draggable,
  onDragStart,
  onDragEnd,
}: Props) {
  const t = useTranslations();
  const locale = useLocale();
  const dfLocale = locale.startsWith("es") ? esLocale : enLocale;

  const state = classifyMarker({
    deviceState: placement.device_state,
    lastSampleIso: live?.iso,
  });

  const stateLabelKey =
    placement.device_state === "active"
      ? "sites.overlay.deviceState.active"
      : placement.device_state === "maintenance"
        ? "sites.overlay.deviceState.maintenance"
        : placement.device_state === "inactive"
          ? "sites.overlay.deviceState.inactive"
          : "sites.overlay.deviceState.unknown";

  const badge = live
    ? `${formatValue(live.value)}${live.unit ? ` ${live.unit}` : ""}`
    : "—";

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            draggable={draggable}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            style={{ left: `${placement.x_pct}%`, top: `${placement.y_pct}%` }}
            className={cn(
              "absolute -translate-x-1/2 -translate-y-1/2 rounded-full border-2 px-2 py-0.5 text-xs font-medium shadow tabular-nums hover:scale-110 transition-transform",
              STATE_CLS[state],
            )}
            aria-label={placement.name ?? placement.device_id}
          >
            {badge}
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          <div className="font-medium">
            {placement.name ?? placement.device_id}
          </div>
          <dl className="mt-1 grid grid-cols-[max-content_1fr] gap-x-2 gap-y-0.5">
            <dt className="text-muted-foreground">
              {t("sites.overlay.tooltipState")}
            </dt>
            <dd>{t(stateLabelKey)}</dd>
            {placement.primary_property ? (
              <>
                <dt className="text-muted-foreground">
                  {t("sites.overlay.tooltipProperty")}
                </dt>
                <dd>{placement.primary_property}</dd>
              </>
            ) : null}
            <dt className="text-muted-foreground">
              {t("sites.overlay.tooltipUpdated")}
            </dt>
            <dd>
              {live
                ? formatDistanceToNowStrict(parseISO(live.iso), {
                    addSuffix: true,
                    locale: dfLocale,
                  })
                : t("sites.overlay.tooltipNoSamples")}
            </dd>
          </dl>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
