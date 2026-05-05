"use client";

import * as React from "react";
import { parse, format, isValid } from "date-fns";
import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const DATE_FMT = "dd/MM/yyyy";
const TIME_FMT = "HH:mm";
const COMBINED = `${DATE_FMT} ${TIME_FMT}`;

export interface DateTimeInputProps {
  value: string | null;
  onChange: (iso: string | null) => void;
  ariaLabelDate?: string;
  ariaLabelTime?: string;
  disabled?: boolean;
  className?: string;
}

function fromIso(iso: string | null): { date: string; time: string } {
  if (!iso) return { date: "", time: "" };
  const d = new Date(iso);
  if (!isValid(d)) return { date: "", time: "" };
  return {
    date: format(d, DATE_FMT),
    time: format(d, TIME_FMT),
  };
}

function tryParse(date: string, time: string): Date | null {
  if (!date || !time) return null;
  const d = parse(`${date} ${time}`, COMBINED, new Date());
  return isValid(d) ? d : null;
}

export function DateTimeInput({
  value,
  onChange,
  ariaLabelDate,
  ariaLabelTime,
  disabled,
  className,
}: DateTimeInputProps) {
  const t = useTranslations();
  const [shadow, setShadow] = React.useState<{ date: string; time: string }>(
    () => fromIso(value),
  );
  const lastEmittedIso = React.useRef<string | null>(value);

  // Re-sync from outside only when the parent's ISO genuinely
  // changes (and isn't the value we just emitted).
  React.useEffect(() => {
    if (value !== lastEmittedIso.current) {
      setShadow(fromIso(value));
      lastEmittedIso.current = value;
    }
  }, [value]);

  const update = (next: { date: string; time: string }) => {
    setShadow(next);
    if (!next.date && !next.time) {
      lastEmittedIso.current = null;
      onChange(null);
      return;
    }
    const parsed = tryParse(next.date, next.time);
    if (parsed) {
      const iso = parsed.toISOString();
      lastEmittedIso.current = iso;
      onChange(iso);
    } else {
      lastEmittedIso.current = null;
      onChange(null);
    }
  };

  const isError =
    (shadow.date.length > 0 || shadow.time.length > 0) &&
    tryParse(shadow.date, shadow.time) === null;

  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex gap-2">
        <Input
          inputMode="numeric"
          maxLength={10}
          placeholder={t("telemetry.custom.datePlaceholder")}
          value={shadow.date}
          aria-label={ariaLabelDate ?? t("telemetry.custom.datePlaceholder")}
          aria-invalid={isError || undefined}
          disabled={disabled}
          onChange={(e) => update({ ...shadow, date: e.target.value })}
        />
        <Input
          inputMode="numeric"
          maxLength={5}
          placeholder={t("telemetry.custom.timePlaceholder")}
          value={shadow.time}
          aria-label={ariaLabelTime ?? t("telemetry.custom.timePlaceholder")}
          aria-invalid={isError || undefined}
          disabled={disabled}
          onChange={(e) => update({ ...shadow, time: e.target.value })}
        />
      </div>
      {isError ? (
        <p className="text-xs text-destructive">
          {t("telemetry.custom.invalid")}
        </p>
      ) : null}
    </div>
  );
}
