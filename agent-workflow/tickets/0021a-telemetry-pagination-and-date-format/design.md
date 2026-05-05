# Design — Ticket 0021a

## Backend

### Route change (`platform/api/app/routes/telemetry.py`)

The current `get_telemetry` forwards `limit=100` (default) to QL
even when `lastN=1000`, so QL caps at 100. Fix is one line in the
route plus a small bound bump:

- When `lastN` is provided, forward `limit=lastN` to QL.
- When `lastN` is not provided, keep the existing behaviour but
  raise the `limit` upper bound from `1000` to `10000` (QL's
  natural per-page ceiling).

```python
limit_for_ql = lastN if lastN is not None else limit
payload = await ql.query_entity(
    measurement_urn,
    type_="DeviceMeasurement",
    attrs="numValue,unitCode",
    from_date=_to_iso(fromDate),
    to_date=_to_iso(toDate),
    last_n=lastN,
    limit=limit_for_ql,
    offset=offset,
)
```

`limit: Annotated[int, Query(ge=1, le=10000)] = 100` — bound bump
only; default unchanged so nothing else regresses.

### Backend test

`tests/test_telemetry.py::test_query_lastN_not_capped_by_default_limit`:
seed 200 measurements for one attribute via the existing helper
fixtures, then `GET …?controlledProperty=…&lastN=1000` → assert
`len(entries) == 200`. Reuses the `created_ids` / `ql` fixtures
already used by `test_query_lastN_limits_results`. No new infra.

## Frontend

### Custom `<DateTimeInput>` (replaces `<input type="datetime-local">`)

New file `web/src/components/ui/datetime-input.tsx`. Renders two
adjacent shadcn `<Input>`s:

- date input with placeholder `dd/mm/aaaa`, mask-friendly
  (`maxLength=10`, accepts only digits + `/`).
- time input with placeholder `HH:mm`, `maxLength=5`.

Internal state holds the two raw strings. On every change we try
to `parse(date + " " + time, "dd/MM/yyyy HH:mm", new Date(), {
locale: es })` from `date-fns`. If valid → emit `iso = d.toISOString()`
to `onChange`. If invalid AND non-empty → set `error: true` and emit
`null`. Empty fields → emit `null` with no error.

Public API:
```ts
export interface DateTimeInputProps {
  value: string | null;       // ISO-8601 in, or null
  onChange: (iso: string | null) => void;
  ariaLabelDate?: string;
  ariaLabelTime?: string;
  disabled?: boolean;
}
```

The component is a controlled wrapper but keeps an internal
`{date, time}` shadow so a parent passing `value=null` doesn't
clobber the user's mid-typing state. `value` only re-syncs when it
changes from outside (effect compares prev ISO).

i18n keys (under `telemetry.custom.*`):
- `datePlaceholder` → `dd/mm/aaaa` (es) / `dd/mm/yyyy` (en)
- `timePlaceholder` → `hh:mm`
- `invalid` → `Fecha u hora no válida` / `Invalid date or time`

### `telemetry-tab.tsx` rewiring

- Replace the two `<input type="datetime-local">` blocks with two
  `<DateTimeInput>`s. `customFrom` / `customTo` continue to hold
  ISO strings (today they hold `YYYY-MM-DDTHH:mm`, which the
  existing `rangeWindow` already passes to `new Date(...)`); we
  promote them to full ISO. `rangeWindow` keeps working unchanged
  because `new Date(iso).toISOString()` is a no-op for ISO input.

### Raw-table pagination

Add three pieces:

1. `web/src/lib/paginate.ts` — pure helper:
   ```ts
   export const PAGE_SIZE = 100;
   export function paginate<T>(items: T[], page: number, pageSize = PAGE_SIZE) {
     const total = items.length;
     const totalPages = Math.max(1, Math.ceil(total / pageSize));
     const clamped = Math.min(Math.max(1, page), totalPages);
     const start = (clamped - 1) * pageSize;
     return { page: clamped, totalPages, items: items.slice(start, start + pageSize) };
   }
   ```
2. `web/src/lib/paginate.test.ts` — covers empty list, single page,
   exact boundary, page < 1, page > totalPages.
3. In `telemetry-tab.tsx`, hold a `tablePage` state. Reset to `1`
   whenever `cp`, `range`, `customFrom`, or `customTo` changes
   (single `useEffect` with those deps). Apply `paginate()` to the
   already-sorted entries (descending), render the slice, and
   show a small footer with prev/next buttons + `t("telemetry.table.pageOf",
   { page, total })`.

### i18n

`telemetry.custom.{datePlaceholder, timePlaceholder, invalid}` and
`telemetry.table.{prev, next, pageOf}` in both `en.json` and
`es.json`.

## Risks / non-risks

- The route `limit` bound goes from 1000 to 10000. No existing
  caller passes `limit` explicitly (FE only passes `lastN`), so no
  client-side change is needed and the public contract widens but
  doesn't break.
- The `DateTimeInput` is locale-stable (we hard-code `dd/MM/yyyy
  HH:mm`); if we later want en US ordering we can branch on
  `useLocale()` in one place. Out of scope for this ticket.
- The shadow state in `DateTimeInput` could drift from the parent
  if the parent resets `value` mid-typing; we accept this because
  the only writer is the same component (the page never resets
  these values programmatically).
