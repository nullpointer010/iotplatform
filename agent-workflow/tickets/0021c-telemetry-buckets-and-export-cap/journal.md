# Journal — Ticket 0021c

## 2026-05-06
- First attempt: server-side fan-out of three QuantumLeap calls
  (avg/min/max) merged in the route to render a min/max envelope
  on the chart. Implemented end-to-end and tests went green.
- User pivot: "Stop. I don't want min/max/avg, I want the data in
  the plot". Rolled back the envelope strategy.
- Final strategy (approved): hybrid two-query model.
  - **Chart**: bucketed `avg` only (one QL call) for `24h` / `7d` /
    `custom` ranges where raw data would be too dense to render.
    For `1h` the chart consumes the raw query directly — no
    aggregation.
  - **Table & CSV**: real samples from a separate raw query
    (`lastN=1000`), always. Aggregates never leak into the
    exported data.
  This keeps the chart fast and readable without hiding samples
  from the analyst's table or export.
- Decision: drop `30d` from the range bar. With minute-bucketing
  on `7d` (~10 080 points worst-case, 168 with hour-buckets) the
  next reasonable step is day-buckets, which the `Personalizado`
  auto-pick already covers.
- Decision: CSV stays raw and FE-built, capped at 100 000 rows.
  Streaming server-side export is overkill for v1.
- Surprise: QuantumLeap indexes telemetry by `TimeInstant`
  (notification-receipt time), not by `dateObserved`. The first
  bucketed integration test asserted two minute-buckets based on
  synthetic `dateObserved` timestamps and got 0 entries. Switched
  to `aggrPeriod=day` (one deterministic bucket) and assert the
  avg matches `mean(values)` — robust across runs.
- Best-effort `total` via QL `?options=count` reads the
  `Fiware-Total-Count` response header; if absent or QL errors,
  `total` is `None` and the FE simply doesn't gate export.

## Lessons (to propagate on close)
- → `memory/gotchas.md`: QL indexes by `TimeInstant`, not
  `dateObserved`; integration tests filtering by `fromDate`/`toDate`
  must use real-time-relative windows or skip the filter.
- → `memory/patterns.md`: when only one aggregator method is
  needed, prefer **chart bucketed-avg + separate raw query** over
  fan-out + envelope. Raw stays exportable; chart stays fast.
