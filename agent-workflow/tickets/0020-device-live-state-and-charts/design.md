# Design — Device live state and charts

## Architecture summary

All work is in `web/`. No backend changes. Three independent UI
features share a thin layer of helpers (`api.getState`, freshness
utilities, CSV builder, sparkline component).

```
web/src/
├── lib/
│   ├── api.ts                 (+ getState)
│   ├── types.ts               (+ DeviceStateDTO)
│   └── freshness.ts           (NEW)
├── components/
│   ├── charts/
│   │   ├── sparkline.tsx      (NEW)
│   │   └── time-series-chart.tsx (NEW)
│   ├── ui/
│   │   └── freshness-badge.tsx (NEW)
│   └── forms/
│       └── data-types-editor.tsx (NEW)
├── app/
│   ├── page.tsx               (+ "Últimas medidas" card)
│   └── devices/[id]/
│       ├── page.tsx           (+ "Estado" tab)
│       ├── state-tab.tsx      (NEW)
│       └── telemetry-tab.tsx  (REWRITTEN)
└── i18n/messages/{es,en}.json (+ keys)
```

Single new dependency: `recharts` (peer-compatible with React 18,
~80 kB gzipped). No other deps.

## 1. State tab

### Endpoint mapping
- `GET /api/v1/devices/{id}/state` → `StateResponse`
  - top-level: `deviceState`, `dateLastValueReported`, `batteryLevel`
  - `attributes`: `{ [attr]: { type, value } }` for everything that
    isn't device metadata. Includes `controlledProperty` values
    plus anything else the bridge has written.

### TS mirror (`lib/types.ts`)
```ts
export interface DeviceStateDTO {
  deviceState?: DeviceState;
  dateLastValueReported?: string;
  batteryLevel?: number;
  attributes?: Record<string, { type: string; value: unknown }>;
}
```

### `api.getState`
```ts
getState: (id: string) =>
  request<DeviceStateDTO>(`/devices/${encodeURIComponent(id)}/state`),
```

### Freshness logic (`lib/freshness.ts`)
```ts
export type Freshness = "fresh" | "stale" | "no-data";

export function freshnessOf(
  iso: string | undefined,
  pollSeconds = 15,
): Freshness {
  if (!iso) return "no-data";
  const ageS = (Date.now() - new Date(iso).getTime()) / 1000;
  if (ageS < pollSeconds * 4) return "fresh"; // ≈ 60 s for 15 s poll
  return "stale";
}
```
"Hace X" formatting reuses `date-fns`'s `formatDistanceToNowStrict`
with the active locale.

### Component layout
`state-tab.tsx`:
- `useQuery({ queryKey: ["state", id], queryFn: api.getState,
  refetchInterval: 15000 })`.
- Top row: status pills for `deviceState` (with color),
  `dateLastValueReported` (relative + absolute), `batteryLevel`.
- One card per attribute in `attributes`:
  - Header: attr name, freshness badge.
  - Body: value (formatted), unit (looked up via
    `device.dataTypes` / unit map; fallback `—`), "actualizado
    hace 12 s".
  - Footer: 1 h sparkline, fed by
    `api.getTelemetry({ controlledProperty: attr, lastN: 60 })`.
    Different `queryKey`, polled at 60 s, suspended when attr is
    declared `Text`.
- Empty `attributes` → `EmptyState` with hint about ingestion.

The `dateObserved` for freshness comes from the matching telemetry
response when available, falling back to top-level
`dateLastValueReported` from the state payload.

### Sparkline
`components/charts/sparkline.tsx`:
- Recharts `<LineChart>` ~80×24 px, no axes/grid/tooltip.
- One `<Line dot={false} strokeWidth={1.5} isAnimationActive={false} />`.
- Color via CSS var (`stroke="hsl(var(--primary))"`).

## 2. Telemetría tab v2

Rewrite of `telemetry-tab.tsx`. Same query helpers, new UI.

### Controls (top card)
- Attribute selector (existing logic).
- Range pills: **24 h | 7 d | 30 d | Custom**.
  - 24 h → `fromDate = now - 24h`, `toDate = now`, `lastN = 1000`.
  - 7 d / 30 d analogous, with `lastN = 1000`.
  - Custom: two `<Input type="datetime-local">`.
- "Export CSV" button (disabled when there's no data).

### Chart
`components/charts/time-series-chart.tsx`:
- Recharts `<ResponsiveContainer>` + `<LineChart>` ~280 px tall.
- X axis: timestamps formatted by range (`HH:mm` for 24 h,
  `dd MMM` otherwise).
- Y axis: numeric, with `unitCode` as label.
- Tooltip: timestamp + `value unitCode`.
- Empty / loading / error states match the existing app patterns.

### CSV export
Pure client-side:
```ts
const csv = [
  "dateObserved,numValue,unitCode",
  ...entries.map(e => `${e.dateObserved},${e.numValue},${e.unitCode ?? ""}`),
].join("\n");
const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
// trigger anchor download, then URL.revokeObjectURL.
```
Filename: `<deviceId>_<attr>_<fromIso>_<toIso>.csv`.

The flat table from v1 is kept under `<details>` for raw inspection.

## 3. `dataTypes` editor

`components/forms/data-types-editor.tsx`:
- Props: `value: Record<string, "Number" | "Text"> | undefined`,
  `onChange(next)`, `availableProperties: string[]` (from
  `controlledProperty`).
- UI: list of rows `[Select(prop)][Select(type)][× button]`, plus
  "Add row" button.
- Validation: duplicate prop blocks save and surfaces a warning.

In `device-form.tsx`:
- Replace the `dataTypesJson` `<Textarea>` block in the MQTT
  section with `<Controller name="dataTypes" …>` rendering
  `<DataTypesEditor>`.
- Form state stores the `Record<string, "Number"|"Text">` directly.
- Submit shape unchanged — backend already accepts that exact
  payload.
- The `tryJson` path is removed.

If a device's stored `dataTypes` contains values other than
`"Number"` / `"Text"`, the editor coerces them to `"Text"` and
shows a one-line warning. No data is silently dropped.

## 4. Dashboard "Últimas medidas" card

`app/page.tsx`:
- New `<RecentMeasurements />` component below the existing cards.
- Uses the dashboard's already-loaded device list. For each device
  with a `controlledProperty`, fires
  `getTelemetry({ controlledProperty: cp[0], lastN: 1 })` (one
  query per device, but bounded by the visible-devices list).
- React Query batches via stable keys; concurrency cap of 5
  in-flight with chunked `Promise.all`.
- Sorts by `dateObserved` desc, takes top 5, renders a `<Table>`:
  device link, attr, value+unit, "hace …".
- Refetches every 30 s.

For large fleets this is O(N) requests; **FU**: backend
`/devices/last-values` aggregate endpoint.

## i18n

New keys in both `messages/en.json` and `messages/es.json`:

- `device.tab.state` → "Estado" / "Status"
- `state.empty.title`, `state.empty.hint`
- `state.updatedAgo` ("hace {n}" / "{n} ago")
- `freshness.fresh`, `freshness.stale`, `freshness.noData`
- `telemetry.range.24h`, `telemetry.range.7d`,
  `telemetry.range.30d`, `telemetry.range.custom`
- `telemetry.exportCsv`
- `device.dataTypes.title`, `device.dataTypes.hint`,
  `device.dataTypes.addRow`, `device.dataTypes.duplicate`,
  `device.dataTypes.empty`
- `dashboard.recent.title`, `dashboard.recent.empty`

## Tests

Web (`vitest`):
- `freshness.test.ts` — pure-function coverage (`fresh`, `stale`,
  `no-data`, boundary at `4 × poll`).
- `data-types-editor.test.tsx` — render with value, add/remove
  rows, assert `onChange` payloads.
- `state-tab.test.tsx` — mock `api.getState`, assert freshness
  badge + Empty state.
- New telemetry test asserts CSV export calls
  `URL.createObjectURL` with a blob whose text starts with the
  header row.

API: nothing to change.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Recharts bundle weight | Tree-shaken imports; dashboard chart imported lazily via `next/dynamic`. |
| Polling stampede on 100+ devices | Cap 5 concurrent telemetry queries; 30 s `staleTime`; FU for `/devices/last-values`. |
| Client/server clock skew | Trust server timestamp; freshness threshold is 4× poll (generous). |
| `dataTypes` with non-`Number`/`Text` values | Editor coerces to `Text` + warns; nothing is silently dropped. |
| Recharts SSR | Chart components are `"use client"` only. |

## Out of scope reminders
- No WebSocket / SSE.
- No new backend route.
- No floorplan changes (0021).
- No uPlot.
