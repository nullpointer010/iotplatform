# Ticket 0021c — telemetry-buckets-and-export-cap

## Problem

`GET /devices/{id}/telemetry` always returns raw rows. With current
ingest (~300 k rows/day for a busy device), `lastN ≤ 1000` means
the chart's "7 d" tab actually only shows the latest few minutes
of data. Raising `lastN` would push millions of rows into the
browser and CrateDB on every render. The fix is **server-side
aggregation for the chart only**, while the raw table and CSV
export keep returning real measurements.

## Goal

Charts always reflect the chosen window using bucketed averages
(one point per bucket, one line). The raw table always shows real
samples. CSV export always emits real samples, capped at a safe
size.

## Range buttons

Drop `30d`. New set: **1h · 24h · 7d · Personalizado**. Default
selected range stays `24h`.

## Bucket map (chart only)

| Range          | Aggregation                                           | Max points |
| -------------- | ----------------------------------------------------- | ---------- |
| 1 h            | none (raw, `lastN=1000` latest)                       | ≤ 1 000    |
| 24 h           | `aggrMethod=avg` · `aggrPeriod=minute`                | 1 440      |
| 7 d            | `aggrMethod=avg` · `aggrPeriod=hour`                  | 168        |
| Personalizado  | auto by span: ≤ 2 h → second, ≤ 2 d → minute,         | ≤ ~720     |
|                | ≤ 30 d → hour, > 30 d → day                           |            |

QuantumLeap only exposes `second | minute | hour | day` as bucket
periods, so "30 s" / "2 min" aren't options; the table above is
the densest grid we can hit while staying inside QL's contract.
The chart line is `numValue = avg(bucket)`. **No min/max band.**

## Raw table policy

Always raw. The table consumes a **separate** raw query — it is
not derived from the bucketed chart series. We fetch the latest
`lastN=1000` real samples for the selected window and paginate
client-side at 100/page. For long windows (7 d) the table is an
"inspection" affordance: it shows the most recent 1 000 raw rows
in that window, not the full history. This is intentional —
multi-million-row tables are not a useful UI.

When the range is `1h` the chart and the table consume the same
raw query (no second request).

## CSV export

CSV always exports **raw** samples for the selected window — never
aggregates.

- Backend returns a `total` field on raw responses (cheap count
  via QL's `?options=count`) so the FE knows whether to allow the
  export.
- If the projected raw row count exceeds **100 000**, the export
  button is disabled with an inline message:
  *"Demasiados datos para exportar (más de 100 000 filas). Si
  necesitas más, consulta al administrador."* / *"Too much data
  to export (more than 100 000 rows). If you need more, contact
  your administrator."*
- Below 100 000, the FE pages QL via `offset` until exhausted and
  builds the CSV in-memory.

## Acceptance criteria

### Backend
- [ ] **A.1** `GET /api/v1/devices/{id}/telemetry` accepts new
  query params:
  - `aggrMethod`: enum `none | avg` (default `none` = raw,
    current behaviour).
  - `aggrPeriod`: enum `second | minute | hour | day` (required
    when `aggrMethod != none`, otherwise rejected).
  - When `aggrMethod = avg`, `lastN` is ignored and the response
    carries one entry per bucket (`numValue = avg`).
- [ ] **A.2** When the range is bucketed, the route makes **one**
  QL call with `aggrMethod=avg` + `aggrPeriod=<p>`. No fan-out, no
  min/max envelope. Response shape:
  ```
  TelemetryResponse {
    deviceId, controlledProperty, aggrMethod, aggrPeriod,
    entries: [{ dateObserved, numValue, unitCode? }]
  }
  ```
- [ ] **A.3** New optional `total` field on raw responses (cheap
  count via QL's `?options=count`) so the FE can pre-validate the
  export cap. Bucketed responses don't need `total`.
- [ ] **A.4** Backend tests:
  - `test_telemetry_avg_bucket`: seed measurements,
    `aggrMethod=avg&aggrPeriod=day`, assert one bucket whose
    `numValue` equals the average of the seeded values.
  - `test_telemetry_aggrPeriod_required_when_method_set` → 422.
  - `test_telemetry_aggrMethod_invalid_value` → 422 (only
    `none|avg` accepted).
  - `test_raw_response_includes_total_count`: raw response has a
    sensible `total >= len(entries)`.

### Frontend
- [ ] **A.5** `time-series-chart.tsx` is a plain `<LineChart>` with
  one line (`numValue`). No min/max band, no `<Area>`, no
  `<ComposedChart>`.
- [ ] **A.6** `telemetry-tab.tsx` ranges become `1h | 24h | 7d |
  custom` (drop `30d`). Each range maps to `(aggrMethod, aggrPeriod)`
  via a small pure helper `pickAggregation(range, fromDate?, toDate?)`
  in `web/src/lib/telemetry-bucket.ts`. The helper also implements
  the Personalizado auto-pick rule.
- [ ] **A.7** When the chosen range is bucketed, the tab issues
  **two** parallel react-queries:
  - `chartQ` → bucketed avg (feeds the chart only).
  - `rawQ`   → raw with `lastN=1000` (feeds the table + CSV).

  When the range is `1h`, only `rawQ` is issued (chart and table
  both consume it).
- [ ] **A.8** Raw table headers are `ts | value | unit` — always
  raw, never bucketed. Pagination 100/page as today.
- [ ] **A.9** CSV export always emits raw rows
  (`dateObserved,localTime,numValue,unitCode`). When `rawQ.total`
  exceeds 100 000 the Export button is disabled and an inline
  warning appears (i18n keys `telemetry.export.tooMany.title`,
  `telemetry.export.tooMany.body`).
- [ ] **A.10** Vitest unit tests for `pickAggregation` covering
  every range and three Personalizado spans (1 h / 1 d / 60 d).
- [ ] **A.11** i18n: drop `telemetry.range.30d`. Add
  `telemetry.range.1h`, `telemetry.export.tooMany.{title,body}`,
  `telemetry.col.{ts,value,unit}` (no `col.min` / `col.max`).

### Verification
- [ ] **A.12** `make test`, `npm test`, `npm run lint`,
  `npx tsc --noEmit` all clean.

## Out of scope

- Streaming server-side CSV export (current FE-side merge is fine
  up to 100 k).
- Per-tenant export-cap configuration.
- Down-sampling for the live overlay (0021); that one stays
  `lastN=1`.
- Switching from QuantumLeap aggregation to a CrateDB direct
  query.
- min/max envelope or any other visual aid beyond the avg line.

## Approved 2026-05-06 (revised)

User confirmed: drop `30d`; chart bucketed by avg only ("if hour
plot them by 30 sec [closest QL grid: minute], if 24 h per minute
or two [closest: minute] etc — you decide the max the plot can
handle"); raw table and CSV must remain raw, never aggregated.
