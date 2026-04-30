"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { ArrowLeft, ImagePlus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Gate } from "@/components/gate";
import { DeleteConfirm } from "@/components/delete-confirm";
import { api } from "@/lib/api";
import { useMutateWithToast } from "@/lib/mutate";
import { toast } from "@/components/ui/use-toast";
import type { Placement } from "@/lib/types";

const MAX_BYTES = 10 * 1024 * 1024;

export default function SiteFloorplanPage() {
  const params = useParams<{ siteArea: string }>();
  const siteArea = decodeURIComponent(String(params.siteArea ?? ""));
  const t = useTranslations("sites");
  const tNav = useTranslations("nav");
  const qc = useQueryClient();

  const sites = useQuery({ queryKey: ["sites"], queryFn: () => api.listSites() });
  const placements = useQuery({
    queryKey: ["placements", siteArea],
    queryFn: () => api.listPlacements(siteArea),
    enabled: !!siteArea,
  });

  const summary = sites.data?.find((s) => s.site_area === siteArea);
  const hasPlan = summary?.has_floorplan ?? false;
  // Bust the image cache when a new plan is uploaded.
  const [planVersion, setPlanVersion] = React.useState(0);

  const upload = useMutateWithToast({
    mutationFn: (file: File) => api.uploadFloorplan(siteArea, file),
    onSuccess: () => {
      setPlanVersion((v) => v + 1);
      qc.invalidateQueries({ queryKey: ["sites"] });
    },
    errorKey: "sites.uploadFailed",
  });

  const remove = useMutateWithToast({
    mutationFn: () => api.deleteFloorplan(siteArea),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sites"] });
    },
    successKey: "toast.deleted",
    errorKey: "toast.deleteFailed",
  });

  const save = useMutateWithToast({
    mutationFn: (vars: { deviceId: string; x_pct: number; y_pct: number }) =>
      api.savePlacement(vars.deviceId, { x_pct: vars.x_pct, y_pct: vars.y_pct }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["placements", siteArea] });
    },
    errorKey: "sites.saveFailed",
  });

  const removePlacement = useMutateWithToast({
    mutationFn: (deviceId: string) => api.deletePlacement(deviceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["placements", siteArea] });
    },
    successKey: "toast.deleted",
    errorKey: "toast.deleteFailed",
  });

  const fileRef = React.useRef<HTMLInputElement>(null);
  function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    if (f.size > MAX_BYTES) {
      toast({ title: t("tooLarge"), variant: "destructive" });
      return;
    }
    if (!["image/png", "image/jpeg", "image/webp"].includes(f.type)) {
      toast({ title: t("notImage"), variant: "destructive" });
      return;
    }
    upload.mutate(f);
  }

  const planUrl = hasPlan
    ? `${api.floorplanUrl(siteArea)}?v=${planVersion}`
    : null;
  const placed = (placements.data ?? []).filter(
    (p): p is Placement & { x_pct: number; y_pct: number } =>
      p.x_pct !== null && p.y_pct !== null,
  );
  const unplaced = (placements.data ?? []).filter(
    (p) => p.x_pct === null || p.y_pct === null,
  );

  // Drag state: which device id is being dragged. Used to also pick up an
  // already-placed marker and re-position it.
  const [dragId, setDragId] = React.useState<string | null>(null);

  function onPlanDragOver(e: React.DragEvent) {
    if (dragId) e.preventDefault();
  }
  function onPlanDrop(e: React.DragEvent) {
    e.preventDefault();
    if (!dragId) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    const x_pct = Math.max(0, Math.min(100, Math.round(x * 10) / 10));
    const y_pct = Math.max(0, Math.min(100, Math.round(y * 10) / 10));
    save.mutate({ deviceId: dragId, x_pct, y_pct });
    setDragId(null);
  }

  return (
    <div className="container space-y-6 py-8">
      <div className="space-y-1">
        <Link
          href="/sites"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" aria-hidden /> {tNav("sites")}
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">{siteArea}</h1>
          <div className="flex items-center gap-2">
            <Gate roles={["operator", "maintenance_manager"]}>
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={onPickFile}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileRef.current?.click()}
                disabled={upload.isPending}
              >
                <ImagePlus className="size-4" aria-hidden />
                {upload.isPending
                  ? t("uploading")
                  : hasPlan
                    ? t("replace")
                    : t("uploadButton")}
              </Button>
            </Gate>
            {hasPlan ? (
              <Gate roles={[]}>
                <DeleteConfirm
                  title={t("deletePlanConfirmTitle")}
                  description={t("deletePlanConfirmDesc")}
                  onConfirm={() => remove.mutate(undefined)}
                  trigger={
                    <Button type="button" variant="ghost" size="sm">
                      <Trash2 className="size-4" aria-hidden />
                      {t("deletePlan")}
                    </Button>
                  }
                />
              </Gate>
            ) : null}
          </div>
        </div>
      </div>

      {hasPlan && planUrl ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
          <div
            className="relative overflow-hidden rounded-lg border bg-muted/20"
            onDragOver={onPlanDragOver}
            onDrop={onPlanDrop}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={planUrl}
              alt={siteArea}
              className="block w-full select-none"
              draggable={false}
            />
            {placed.map((p) => (
              <button
                key={p.device_id}
                type="button"
                draggable
                onDragStart={() => setDragId(p.device_id)}
                onDragEnd={() => setDragId(null)}
                style={{
                  left: `${p.x_pct}%`,
                  top: `${p.y_pct}%`,
                }}
                className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground shadow hover:scale-110"
                title={p.name ?? p.device_id}
              >
                {p.name ?? "•"}
              </button>
            ))}
          </div>
          <aside className="space-y-3">
            <h2 className="text-sm font-semibold">
              {t("unplacedDevices")}{" "}
              <Badge variant="secondary">{unplaced.length}</Badge>
            </h2>
            <p className="text-xs text-muted-foreground">{t("unplacedHint")}</p>
            <ul className="space-y-2">
              {unplaced.map((p) => (
                <li key={p.device_id}>
                  <Gate
                    roles={["operator", "maintenance_manager"]}
                    fallback={
                      <div className="rounded-md border bg-card px-3 py-2 text-sm">
                        {p.name ?? p.device_id}
                      </div>
                    }
                  >
                    <div
                      draggable
                      onDragStart={() => setDragId(p.device_id)}
                      onDragEnd={() => setDragId(null)}
                      className="cursor-grab rounded-md border bg-card px-3 py-2 text-sm hover:bg-accent active:cursor-grabbing"
                    >
                      {p.name ?? p.device_id}
                    </div>
                  </Gate>
                </li>
              ))}
            </ul>
            {placed.length > 0 ? (
              <>
                <h2 className="pt-4 text-sm font-semibold">
                  {t("placedDevices")}{" "}
                  <Badge variant="secondary">{placed.length}</Badge>
                </h2>
                <ul className="space-y-2">
                  {placed.map((p) => (
                    <li
                      key={p.device_id}
                      className="flex items-center justify-between rounded-md border bg-card px-3 py-2 text-sm"
                    >
                      <Link
                        href={`/devices/${encodeURIComponent(p.device_id)}`}
                        className="hover:underline"
                      >
                        {p.name ?? p.device_id}
                      </Link>
                      <Gate roles={[]}>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removePlacement.mutate(p.device_id)}
                          aria-label={t("removePlacement")}
                        >
                          <Trash2 className="size-4" aria-hidden />
                        </Button>
                      </Gate>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </aside>
        </div>
      ) : (
        <EmptyState
          title={t("noPlanTitle")}
          description={t("noPlanHint")}
        />
      )}
    </div>
  );
}
