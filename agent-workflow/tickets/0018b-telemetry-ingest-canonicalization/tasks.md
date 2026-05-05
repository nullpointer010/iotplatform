# Tasks — Ticket 0018b

- [x] T1 Add `_upsert_measurement(device_urn, attr, value, ts_iso)` on
      `MqttBridge` (private async method) doing
      `create_entity` → on `DuplicateEntity` → `patch_entity`. Log
      `OrionError` at WARNING; never raise.
- [x] T2 Update `_forward` to (a) add `dateLastValueReported` to
      every Device patch, (b) call `_upsert_measurement` when
      `ngsi_type == "Number"`.
- [x] T3 Add three integration tests in
      `platform/api/tests/test_mqtt_bridge.py`:
      `test_publish_lands_in_state_and_telemetry`,
      `test_two_publishes_yield_two_entries`,
      `test_boolean_publish_creates_no_measurement`.
- [x] T4 `make test` — 170 passed, 1 pre-existing flake
      (`test_query_lastN_limits_results`, tracked since 0011).
      0018b's 10 MQTT tests all green.
- [x] T5 Update `agent-workflow/architecture.md` "Ingestion
      (current)" subsection — caveat removed, dual-write described.
- [x] T6 Tick the deferred "publish appears in `/telemetry`" task in
      `0018-mqtt-broker-and-bridge/tasks.md` with `(closed by 0018b)`.
- [x] T7 Fill `journal.md` and `review.md`; flip `status.md` to
      `done`; commit.
