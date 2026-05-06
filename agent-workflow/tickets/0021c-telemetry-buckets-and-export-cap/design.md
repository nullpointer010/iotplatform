# Design — 0021c (revised 2026-05-06)

## Backend

### `app/quantumleap.py::query_entity`
Forward-only kwargs:
- `aggr_method: str | None` → QL `aggrMethod`
- `aggr_period: str | None` → QL `aggrPeriod`
- `options: str | None` → QL `options`

Plus a sibling `count_entity(...)` that issues a
`?limit=1&options=count` request and reads the
`Fiware-Total-Count` header. (Already implemented in the previous
pass; keep as-is.)

### `app/schemas_telemetry.py`
```python
AggrMethod = Literal["none", "avg"]
AggrPeriod = Literal["second", "minute", "hour", "day"]

class TelemetryEntry:
    dateObserved: str
    numValue: float
    unitCode: str | None = None
    # NO minValue / maxValue.

class TelemetryResponse:
    deviceId: str
    controlledProperty: str
    aggrMethod: AggrMethod = "none"
    aggrPeriod: AggrPeriod | None = None
    total: int | None = None        # raw mode only
    entries: list[TelemetryEntry]
```

### `app/routes/telemetry.py::get_telemetry`
Query params:
```python
aggrMethod: Literal["none", "avg"] = "none"
aggrPeriod: Literal["second","minute","hour","day"] | None = None
```
- 422 if `aggrMethod != "none"` and `aggrPeriod is None`.
- If raw (`aggrMethod == "none"`): existing path; additionally
  call `ql.count_entity(...)` and set `total` on the response
  (best-effort: leave `None` on QL error).
- If bucketed (`aggrMethod == "avg"`): single QL call with
  `attrs="numValue"`, `aggrMethod="avg"`, `aggrPeriod=<p>`,
  same `fromDate`/`toDate`. `lastN`/`limit`/`offset` ignored.
  Return one entry per bucket index with `numValue = avg`.
  No `total`.

## Frontend

### `web/src/lib/telemetry-bucket.ts` (already exists)
```ts
export type TimeSeriesRange = "1h" | "24h" | "7d" | "custom";
export interface AggregationChoice {
  aggrMethod: "none" | "avg";
  aggrPeriod?: "second" | "minute" | "hour" | "day";
}
export function pickAggregation(
  range: TimeSeriesRange,
  fromIso?: string,
  toIso?: string,
): AggregationChoice;
```
Rules unchanged from previous draft:
- `1h` → `{ aggrMethod: "none" }` (raw, `lastN=1000`).
- `24h` → `{ aggrMethod: "avg", aggrPeriod: "minute" }`.
- `7d`  → `{ aggrMethod: "avg", aggrPeriod: "hour" }`.
- `custom` with span `Δ`:
  - Δ ≤ 2 h → `second`
  - Δ ≤ 2 d → `minute`
  - Δ ≤ 30 d → `hour`
  - else → `day`
  Missing dates → fall back to `hour`.

### `web/src/lib/api.ts::getTelemetry`
Forward `aggrMethod` / `aggrPeriod`. (Already done.)

### `web/src/lib/types.ts`
Drop `minValue` / `maxValue` from `TelemetryEntry`. Keep
`aggrMethod`, `aggrPeriod`, `total` on the response.

### `web/src/components/charts/time-series-chart.tsx`
Plain `<LineChart>` with one `<Line>` on `dataKey="v"`. No
`<Area>`, no band logic, no `<ComposedChart>`. Each point is
`{ t, v }`; `lo`/`hi` removed from the public type.

### `web/src/app/devices/[id]/telemetry-tab.tsx`
Two parallel queries:
- `chartQ`: enabled when bucketed; calls
  `getTelemetry(... aggrMethod, aggrPeriod)`. Powers the chart.
- `rawQ`: always enabled; calls `getTelemetry(... lastN: 1000)`.
  Powers the table and CSV. Provides `total` for the export gate.

When `range === "1h"`, `chartQ` is disabled and the chart consumes
`rawQ` directly (avoids a duplicate request).

Loading / error states wait for whichever queries are enabled.

### CSV / table
- Table headers: `ts | value | unit`. Always raw rows from `rawQ`.
- CSV: existing raw builder. Disabled when
  `rawQ.total > 100_000`.

### i18n (`en.json`, `es.json`)
- Drop `telemetry.range.30d`.
- Add `telemetry.range.1h`, `telemetry.export.tooMany.{title,body}`,
  `telemetry.col.{ts,value,unit}`. **No** `col.min` / `col.max`.

## Tests

### Backend (`tests/test_telemetry.py`)
Replace the avg/min/max test with:
- `test_telemetry_avg_bucket_per_day`: seed N measurements,
  `aggrMethod=avg&aggrPeriod=day`, assert 1 entry with
  `numValue == mean(values)`.
- Keep `test_aggrPeriod_required_when_aggrMethod_set` and
  `test_aggrMethod_invalid_value_returns_422` (now `median`/`min`
  are also rejected since enum is `none|avg`).
- Keep `test_raw_response_includes_total_count`.

### Web (`telemetry-bucket.test.ts`)
Same nine cases as today.

## Out of scope confirmation

Streaming CSV, server-side CSV, alert rules (0022), CrateDB
direct queries, min/max envelopes.
