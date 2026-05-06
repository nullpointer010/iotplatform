# Review — Ticket 0021c

## Self-review (agent)

### What changed
- **Backend**
  - `app/quantumleap.py`: `query_entity` forwards `aggr_method` /
    `aggr_period`; new `count_entity()` reads `Fiware-Total-Count`.
  - `app/schemas_telemetry.py`: `AggrMethod = "none" | "avg"`,
    `AggrPeriod ∈ {second, minute, hour, day}`,
    `TelemetryResponse.{aggrMethod, aggrPeriod, total}`.
  - `app/routes/telemetry.py`: `aggrMethod` / `aggrPeriod` query
    params with 422 on missing `aggrPeriod`; bucketed branch is a
    single QL call with `aggrMethod=avg`; raw branch attaches
    best-effort `total` from `count_entity`.
- **Frontend**
  - `web/src/lib/telemetry-bucket.ts` — pure helper
    `pickAggregation(range, fromIso?, toIso?)` and
    `web/src/lib/telemetry-bucket.test.ts` (9 cases).
  - `web/src/lib/api.ts` + `types.ts` carry the new params; no
    `min`/`max` fields.
  - `web/src/components/charts/time-series-chart.tsx` stays a
    plain `LineChart` of `{t, v}` points.
  - `web/src/app/devices/[id]/telemetry-tab.tsx`:
    ranges become `1h | 24h | 7d | custom`; routes through
    `pickAggregation`; two parallel react-queries — `chartQ`
    (bucketed avg, enabled only when bucketed) and `rawQ` (raw
    samples, always). Chart consumes `chartQ` when bucketed and
    `rawQ` when `range = 1h`. Raw table and CSV always consume
    `rawQ`. Export button disabled with inline `tooMany` warning
    when `rawQ.total > 100 000`.
  - `telemetry-tab.test.ts` updated for the simplified
    `buildCsv(entries)` signature.
- **i18n**: dropped `telemetry.range.30d`; added
  `telemetry.range.1h`, `telemetry.export.tooMany.{title,body}`,
  `telemetry.col.{ts,value,unit}` in `en` and `es` (no `min`/`max`).
- **Tests**: 4 new pytest cases (avg bucket per day,
  `aggrPeriod` required, invalid `aggrMethod` rejected, raw
  `total` smoke). `make test` 189 pass; `npm test` 38 pass;
  `npm run lint` clean; `npx tsc --noEmit` clean.

### Why these changes meet the acceptance criteria
- A.1–A.3 → new query params, single bucketed call,
  `total` via `count_entity`.
- A.4 → `test_avg_bucket_per_day`,
  `test_aggrPeriod_required_when_aggrMethod_set`,
  `test_aggrMethod_invalid_value_returns_422`,
  `test_raw_response_includes_total_count`.
- A.5 → plain line chart of `{t, v}` points; chart auto-bucketed
  for dense ranges, raw for `1h`.
- A.6, A.7 → `telemetry-tab.tsx` rewired through
  `pickAggregation` + two parallel queries.
- A.8 → raw table is real samples, paginated.
- A.9 → CSV cap + i18n warning + disabled button.
- A.10 → 9 vitest cases for `pickAggregation`.
- A.11 → i18n keys updated (`30d` removed, `1h` added,
  `export.tooMany`, `col.{ts,value,unit}`).
- A.12 → all four checks green.

### Known limitations / debt introduced
- `total` is best-effort: if QL doesn't return
  `Fiware-Total-Count` we silently leave it `None` and the export
  cap is not enforced. Acceptable for v1; a follow-up could add a
  small window-scan fallback if real deployments hit this path.
- The bucketed integration test uses `aggrPeriod=day` (one
  bucket) because QL indexes by `TimeInstant`, not the synthetic
  `dateObserved` we push. Multi-bucket assertions would require a
  test that genuinely sleeps across a real wall-clock minute.
- Bucketed mode drops `unitCode` from individual entries (QL
  doesn't aggregate text). The chart's Y-axis label is taken from
  the raw query's first entry, which is always available.
- `rawQ` is always issued (even for `7d`). At 1000 samples this is
  cheap; on extremely chatty devices the table will show "the
  most recent 1000" — by design.

### Suggested follow-up tickets
- 0022 alerts-and-rules (already drafted, blocked by 0021c) is
  now unblocked.
- Optional: extend `pickAggregation` to accept a "max points" knob
  so the FE can request denser buckets on big screens.

## External review

<paste here output from Codex, another model, or a human reviewer>

## Resolution

- [ ] All review comments addressed or filed as new tickets
- [ ] Lessons propagated to `agent-workflow/memory/`
