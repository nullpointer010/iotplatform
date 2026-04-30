"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Eye, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DeleteConfirm } from "@/components/delete-confirm";
import { EmptyState } from "@/components/ui/empty-state";
import { api } from "@/lib/api";
import { useMutateWithToast } from "@/lib/mutate";
import { optimisticListDelete } from "@/lib/optimistic";
import { CATEGORY, PROTOCOL, STATE } from "@/lib/zod";
import type { Device, DeviceState } from "@/lib/types";

const stateVariant: Record<DeviceState, "success" | "warning" | "secondary"> = {
  active: "success",
  maintenance: "warning",
  inactive: "secondary",
};

type SortKey = "name-asc" | "name-desc" | "category-asc" | "state-asc";
const ALL = "__all__";

export default function DevicesPage() {
  const qc = useQueryClient();
  const t = useTranslations();
  const devices = useQuery({
    queryKey: ["devices"],
    queryFn: () => api.listDevices(1000, 0),
  });

  const [q, setQ] = React.useState("");
  const [category, setCategory] = React.useState<string>(ALL);
  const [protocol, setProtocol] = React.useState<string>(ALL);
  const [state, setState] = React.useState<string>(ALL);
  const [sort, setSort] = React.useState<SortKey>("name-asc");

  const filtered = React.useMemo(() => {
    const all = devices.data ?? [];
    const needle = q.trim().toLowerCase();
    let rows = all.filter((d) => {
      if (needle) {
        const hay = `${d.name ?? ""} ${d.id} ${d.modelName ?? ""}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      if (category !== ALL && d.category !== category) return false;
      if (protocol !== ALL && d.supportedProtocol !== protocol) return false;
      if (state !== ALL && d.deviceState !== state) return false;
      return true;
    });
    rows = sortDevices(rows, sort);
    return rows;
  }, [devices.data, q, category, protocol, state, sort]);

  const del = useMutateWithToast<void, string>({
    mutationFn: async (id) => {
      const { rollback } = optimisticListDelete<Device>(
        qc,
        ["devices"],
        (d) => d.id === id,
      );
      try {
        await api.deleteDevice(id);
      } catch (e) {
        rollback();
        throw e;
      }
    },
    successKey: "toast.deleted",
    errorKey: "toast.deleteFailed",
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["devices"] });
    },
  });

  const total = devices.data?.length ?? 0;
  const filtersActive =
    q.length > 0 || category !== ALL || protocol !== ALL || state !== ALL;

  const showEmpty =
    !devices.isLoading && !devices.isError && total === 0 && !filtersActive;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("device.title")}
          </h1>
          <p className="text-sm text-muted-foreground">{t("device.subtitle")}</p>
        </div>
        <Button asChild>
          <Link href="/devices/new">
            <Plus className="mr-2 h-4 w-4" /> {t("device.new")}
          </Link>
        </Button>
      </div>

      {showEmpty ? (
        <EmptyState
          title={t("device.emptyTitle")}
          description={t("device.emptyHint")}
          action={
            <Button asChild>
              <Link href="/devices/new">
                <Plus className="mr-2 h-4 w-4" /> {t("device.new")}
              </Link>
            </Button>
          }
        />
      ) : (
        <>
          <div className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-[1fr_repeat(4,minmax(0,180px))_auto]">
            <div className="space-y-1.5">
              <Label className="text-xs">{t("common.search")}</Label>
              <div className="relative">
                <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="pl-8"
                  placeholder={t("device.list.search")}
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                />
              </div>
            </div>
            <FilterSelect
              label={t("device.list.col.category")}
              value={category}
              options={CATEGORY}
              onChange={setCategory}
              allLabel={t("common.all")}
            />
            <FilterSelect
              label={t("device.list.col.protocol")}
              value={protocol}
              options={PROTOCOL}
              onChange={setProtocol}
              allLabel={t("common.all")}
            />
            <FilterSelect
              label={t("device.list.col.state")}
              value={state}
              options={STATE}
              onChange={setState}
              allLabel={t("common.all")}
            />
            <div className="space-y-1.5">
              <Label className="text-xs">Sort</Label>
              <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="name-asc">A–Z</SelectItem>
                  <SelectItem value="name-desc">Z–A</SelectItem>
                  <SelectItem value="category-asc">{t("device.list.col.category")}</SelectItem>
                  <SelectItem value="state-asc">{t("device.list.col.state")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button
                variant="outline"
                disabled={!filtersActive}
                onClick={() => {
                  setQ("");
                  setCategory(ALL);
                  setProtocol(ALL);
                  setState(ALL);
                }}
              >
                <X className="mr-2 h-4 w-4" /> {t("device.list.clearFilters")}
              </Button>
            </div>
          </div>

          <div className="text-xs text-muted-foreground">
            {filtered.length} / {total}
          </div>

          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("device.list.col.name")}</TableHead>
                  <TableHead>{t("device.list.col.category")}</TableHead>
                  <TableHead>{t("device.list.col.protocol")}</TableHead>
                  <TableHead>{t("device.list.col.state")}</TableHead>
                  <TableHead>{t("device.list.col.siteArea")}</TableHead>
                  <TableHead>{t("device.list.col.owner")}</TableHead>
                  <TableHead className="w-[1%]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.isLoading && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      {t("common.loading")}
                    </TableCell>
                  </TableRow>
                )}
                {devices.isError && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-destructive">
                      {(devices.error as Error)?.message}
                    </TableCell>
                  </TableRow>
                )}
                {!devices.isLoading && !devices.isError && filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      {t("common.empty")}
                    </TableCell>
                  </TableRow>
                )}
                {filtered.map((d) => (
                  <TableRow key={d.id}>
                    <TableCell className="font-medium">
                      <Link
                        href={`/devices/${encodeURIComponent(d.id)}`}
                        className="hover:underline"
                      >
                        {d.name ?? d.id}
                      </Link>
                      <div className="text-xs text-muted-foreground">{d.id}</div>
                    </TableCell>
                    <TableCell>{d.category ?? "—"}</TableCell>
                    <TableCell>{d.supportedProtocol ?? "—"}</TableCell>
                    <TableCell>
                      {d.deviceState ? (
                        <Badge variant={stateVariant[d.deviceState]}>{d.deviceState}</Badge>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {d.location?.site_area ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {d.owner?.join(", ") ?? "—"}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-1">
                        <Button asChild variant="ghost" size="icon" aria-label="View">
                          <Link href={`/devices/${encodeURIComponent(d.id)}`}>
                            <Eye className="h-4 w-4" />
                          </Link>
                        </Button>
                        <Button asChild variant="ghost" size="icon" aria-label={t("common.edit")}>
                          <Link href={`/devices/${encodeURIComponent(d.id)}/edit`}>
                            <Pencil className="h-4 w-4" />
                          </Link>
                        </Button>
                        <DeleteConfirm
                          title={t("device.deleteConfirmTitle")}
                          description={t("device.deleteConfirmDesc")}
                          onConfirm={() => del.mutateAsync(d.id)}
                          trigger={
                            <Button variant="ghost" size="icon" aria-label={t("common.delete")}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          }
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
  allLabel,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (v: string) => void;
  allLabel: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>{allLabel}</SelectItem>
          {options.map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function sortDevices(rows: Device[], key: SortKey): Device[] {
  const copy = [...rows];
  const cmp = (a: string | undefined, b: string | undefined) =>
    (a ?? "").localeCompare(b ?? "");
  switch (key) {
    case "name-asc":
      copy.sort((a, b) => cmp(a.name ?? a.id, b.name ?? b.id));
      break;
    case "name-desc":
      copy.sort((a, b) => cmp(b.name ?? b.id, a.name ?? a.id));
      break;
    case "category-asc":
      copy.sort((a, b) => cmp(a.category, b.category) || cmp(a.name, b.name));
      break;
    case "state-asc":
      copy.sort((a, b) => cmp(a.deviceState, b.deviceState) || cmp(a.name, b.name));
      break;
  }
  return copy;
}
