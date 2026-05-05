"use client";

import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import type { Freshness } from "@/lib/freshness";

const VARIANT: Record<Freshness, "success" | "warning" | "secondary"> = {
  fresh: "success",
  stale: "warning",
  "no-data": "secondary",
};

export function FreshnessBadge({ freshness }: { freshness: Freshness }) {
  const t = useTranslations();
  const labelKey: Record<Freshness, string> = {
    fresh: "freshness.fresh",
    stale: "freshness.stale",
    "no-data": "freshness.noData",
  };
  return <Badge variant={VARIANT[freshness]}>{t(labelKey[freshness])}</Badge>;
}
