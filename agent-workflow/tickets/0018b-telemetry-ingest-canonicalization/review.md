# Review — Ticket 0018b

## What changed
- `platform/api/app/mqtt_bridge.py` (~+55 lines): `_forward` now
  patches `Device` with both `<attr>` and `dateLastValueReported`,
  and (for `Number` only) calls a new private
  `_upsert_measurement(device_urn, attr, value, ts_iso)` doing
  `create_entity` → on `DuplicateEntity` → `patch_entity`. Errors
  log WARNING and never raise.
- `platform/api/tests/test_mqtt_bridge.py` (+3 tests):
  `test_publish_lands_in_state_and_telemetry`,
  `test_two_publishes_yield_two_entries`,
  `test_boolean_publish_creates_no_measurement`.
- `agent-workflow/architecture.md`: "Ingestion (current)" subsection
  rewritten to drop the 0018b TODO and describe the dual write.
- `agent-workflow/tickets/0018-mqtt-broker-and-bridge/tasks.md`:
  deferred telemetry smoke task ticked with `(closed by 0018b)`.
- Ticket 0018b paper trail (status, requirements, design, tasks,
  journal, this review).

No code touched outside `mqtt_bridge.py`. No data-model change. No
new dependency. No new route. No compose / Alembic / front-end
change.

## Acceptance criteria — evidence

- **A.1 `/state` updated + `dateLastValueReported`** —
  `test_publish_lands_in_state_and_telemetry` asserts both.
- **A.2 `/telemetry` returns the value** — same test polls
  `/api/v1/devices/{id}/telemetry?controlledProperty=temperature`
  until at least one entry with `numValue == 24.7` shows up.
- **A.3 `DeviceMeasurement` entity exists with the canonical
  shape** — same test fetches the entity directly from Orion and
  asserts `type`, `refDevice`, `controlledProperty`, `numValue`.
- **A second publish appends, no collision** —
  `test_two_publishes_yield_two_entries`.
- **Boolean publishes skip measurement** —
  `test_boolean_publish_creates_no_measurement`.
- **Invalid payload still drops as 0018** — covered by the
  pre-existing `test_publish_invalid_json_dropped` and
  `test_publish_dataTypes_mismatch_dropped`, unchanged.
- **B `make test` green** — 170 passed; 1 pre-existing flake
  unrelated to this ticket (long-tracked
  `test_query_lastN_limits_results`).
- **C single canonical writer** — `_upsert_measurement` is the
  single chokepoint; 0019 (HTTP/LoRaWAN webhook) reuses it.
- **C architecture doc updated** — "Ingestion (current)" subsection
  rewritten.

## Follow-ups (not in scope)

- **FU1 (0019)** Add HTTP/LoRaWAN webhook ingest that calls
  `_upsert_measurement` (or, if the bridge moves out of the API
  process, an extracted `mqtt_ingest.upsert_measurement(...)`).
- **FU2 (0026)** Surface a counter for `_upsert_measurement`
  warnings on the system health page so silent telemetry gaps are
  observable.
- **FU3 (separate ticket, low priority)** Resolve `unitCode` from a
  controlled-vocabulary mapping (same shape as `UNITS` in
  `add_test_data.py`) and include it in the upsert.
- **FU4 (separate ticket)** Allow MQTT payloads to carry a sensor
  timestamp (`{"value": ..., "ts": "..."}`) and use it as
  `dateObserved` instead of the bridge's wall clock.

## Self-review notes

- The dual write is intentionally non-transactional. The `Device`
  patch happens first; if Orion goes down between the two, `/state`
  will be ahead of `/telemetry` for that one publish. This is the
  documented v1 trade-off (see design.md, Risks). FU2 monitors the
  symptom.
- No counter is added for "successful measurement upserts" — the
  existing `dropped_invalid` is enough for v1, and adding a metric
  without a consumer is speculative.
- The `_wait_until` polling budgets in the new tests (4 s for
  state, 8 s for telemetry) match the pattern used by 0018's
  existing tests. If CI flakes, raising `timeout_s` is the first
  lever.

## External review
(none yet)
