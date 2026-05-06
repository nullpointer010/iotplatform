# Tasks — 0021c

- [x] **T1** Extend `app/quantumleap.py`:
  - Forward `aggr_method`, `aggr_period`, `options` from
    `query_entity` to QL.
  - Add `count_entity(...)` reading `Fiware-Total-Count` header.
- [x] **T2** Update `app/schemas_telemetry.py`:
  - `AggrMethod = Literal["none", "avg"]`,
    `AggrPeriod = Literal["second","minute","hour","day"]`.
  - `TelemetryResponse.aggrMethod`, `aggrPeriod`, `total`.
- [x] **T3** Rewire `app/routes/telemetry.py::get_telemetry`:
  - new `aggrMethod` / `aggrPeriod` query params,
  - 422 when `aggrPeriod` missing,
  - bucketed branch: single QL call with `aggrMethod=avg`,
  - raw branch sets `total` via `count_entity`.
- [x] **T4** Backend tests
  (`tests/test_telemetry.py` additions, see design).
- [x] **T5** Create `web/src/lib/telemetry-bucket.ts` and
  `telemetry-bucket.test.ts`.
- [x] **T6** Update `web/src/lib/types.ts` and
  `web/src/lib/api.ts` (forward new params; `AggrMethod` narrowed
  to `"none" | "avg"`).
- [x] **T7** `web/src/components/charts/time-series-chart.tsx`
  stays a plain line chart (no envelope); `TimeSeriesPoint = {t, v}`.
- [x] **T8** Rewire `web/src/app/devices/[id]/telemetry-tab.tsx`:
  drop `30d`, add `1h`, route through `pickAggregation`, split
  into two react-queries (`chartQ` bucketed avg + `rawQ` raw
  samples; `1h` reuses `rawQ` for the chart). Raw table and CSV
  always consume `rawQ`. CSV cap from `rawQ.total`.
- [x] **T9** i18n updates (`en.json`, `es.json`):
  drop `range.30d`, add `range.1h`, `export.tooMany.{title,body}`,
  `col.{ts,value,unit}` (no `min`/`max`).
- [x] **T10** Verify: `make test`, `cd web && npm test &&
  npm run lint && npx tsc --noEmit`.
- [x] **T11** Manual smoke (user): chart shows real data on `1h`,
  smooth bucketed avg on `24h`/`7d`; raw table shows real samples;
  CSV blocked at >100 k.
- [x] **T12** Close: journal + review + status flip + roadmap +
  commit.
