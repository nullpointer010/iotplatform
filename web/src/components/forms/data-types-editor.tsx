"use client";

import * as React from "react";
import { useTranslations } from "next-intl";
import { Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type DataTypeKind = "Number" | "Text";

interface Row {
  prop: string;
  kind: DataTypeKind;
}

export function parseDataTypes(json?: string): Row[] {
  if (!json) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch {
    return [];
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return [];
  const out: Row[] = [];
  for (const [k, v] of Object.entries(parsed as Record<string, unknown>)) {
    const kind: DataTypeKind = v === "Number" ? "Number" : "Text";
    out.push({ prop: k, kind });
  }
  return out;
}

export function serializeDataTypes(rows: Row[]): string | undefined {
  const cleaned = rows.filter((r) => r.prop.trim().length > 0);
  if (cleaned.length === 0) return undefined;
  const obj: Record<string, DataTypeKind> = {};
  for (const r of cleaned) obj[r.prop.trim()] = r.kind;
  return JSON.stringify(obj);
}

export function DataTypesEditor({
  value,
  onChange,
  availableProperties,
}: {
  value: string | undefined;
  onChange: (next: string | undefined) => void;
  availableProperties: string[];
}) {
  const t = useTranslations();
  const [rows, setRows] = React.useState<Row[]>(() => parseDataTypes(value));

  // Sync from external value changes (e.g. form reset).
  const lastSerializedRef = React.useRef<string | undefined>(serializeDataTypes(rows));
  React.useEffect(() => {
    if (value !== lastSerializedRef.current) {
      setRows(parseDataTypes(value));
      lastSerializedRef.current = value;
    }
  }, [value]);

  const update = (next: Row[]) => {
    setRows(next);
    const ser = serialize(next);
    lastSerializedRef.current = ser;
    onChange(ser);
  };

  const seen = new Set<string>();
  const duplicates = new Set<number>();
  rows.forEach((r, i) => {
    const k = r.prop.trim();
    if (!k) return;
    if (seen.has(k)) duplicates.add(i);
    seen.add(k);
  });

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">{t("dataTypes.hint")}</p>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("dataTypes.empty")}</p>
      ) : (
        <div className="space-y-2">
          {rows.map((row, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="flex-1">
                {availableProperties.length > 0 ? (
                  <PropPicker
                    value={row.prop}
                    options={availableProperties}
                    onChange={(v) => update(rows.map((r, j) => (j === i ? { ...r, prop: v } : r)))}
                  />
                ) : (
                  <Input
                    value={row.prop}
                    placeholder={t("dataTypes.property")}
                    onChange={(e) =>
                      update(rows.map((r, j) => (j === i ? { ...r, prop: e.target.value } : r)))
                    }
                  />
                )}
                {duplicates.has(i) && (
                  <p className="mt-1 text-xs text-destructive">
                    {t("dataTypes.duplicate")}
                  </p>
                )}
              </div>
              <div className="w-32">
                <Select
                  value={row.kind}
                  onValueChange={(v) =>
                    update(rows.map((r, j) => (j === i ? { ...r, kind: v as DataTypeKind } : r)))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Number">Number</SelectItem>
                    <SelectItem value="Text">Text</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={t("dataTypes.remove")}
                onClick={() => update(rows.filter((_, j) => j !== i))}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => update([...rows, { prop: "", kind: "Number" }])}
      >
        {t("dataTypes.addRow")}
      </Button>
    </div>
  );
}

function PropPicker({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  // Allow free text fallback when the value isn't in the options list.
  const known = options.includes(value);
  const [mode, setMode] = React.useState<"select" | "input">(
    known || !value ? "select" : "input",
  );
  if (mode === "input") {
    return (
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={() => {
          if (options.includes(value)) setMode("select");
        }}
      />
    );
  }
  return (
    <Select
      value={value}
      onValueChange={(v) => {
        if (v === "__custom__") {
          setMode("input");
          return;
        }
        onChange(v);
      }}
    >
      <SelectTrigger>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o} value={o}>
            {o}
          </SelectItem>
        ))}
        <SelectItem value="__custom__">…</SelectItem>
      </SelectContent>
    </Select>
  );
}
