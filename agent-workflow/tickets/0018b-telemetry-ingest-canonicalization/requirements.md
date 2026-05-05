# Ticket 0018b — telemetry-ingest-canonicalization

## Problem

The MQTT bridge shipped in 0018 patches the `Device:<id>` entity, so a
publish like `mosquitto_pub -t <root>/temperature -m '{"value": 24.7}'`
moves `GET /api/v1/devices/{id}/state` (the new `attributes.temperature`
slot). It does **not**, however, create or update the corresponding
`urn:ngsi-ld:DeviceMeasurement:<deviceUuid>:Temperature` entity that
`GET /api/v1/devices/{id}/telemetry` queries via QuantumLeap. The
result: real ingestion looks "alive" in `/state` but `/telemetry`
returns an empty `entries` list. This is the gap recorded in 0018a
(`agent-workflow/memory/gotchas.md`, ingestion subsection of
`architecture.md`) and the blocker for every Phase 2 ticket that
consumes time-series data (0019 HTTP/LoRaWAN ingest, 0020 charts,
0021 floor-plan overlay, 0022 alerts).

## Goal

Every successful MQTT publish lands in **both** `/state` and
`/telemetry` for the corresponding `controlledProperty`, without any
restart and without changing the public API contract.

## User stories

- As a sensor operator, I publish a numeric measurement over MQTT and
  see it within seconds in the device's "Telemetría" history, not just
  in "Estado".
- As the agent on a future Phase 2 ticket (0020 charts, 0022 alerts),
  I can rely on `DeviceMeasurement` rows in CrateDB being the single
  source of telemetry truth, regardless of ingest path.
- As a developer of the upcoming 0019 HTTP/LoRaWAN webhook, I reuse
  the same canonical writer so both ingest paths produce identical
  entities.

## Acceptance criteria (verifiable)

### A. Behaviour
- [ ] Publishing `{"value": 24.7}` (or a bare scalar) on
      `<mqttTopicRoot>/<attr>` for an MQTT device whose `dataTypes`
      maps `attr → "Number"` results, within 4 s, in:
    1. `GET /api/v1/devices/{id}/state` showing
       `attributes.<attr>.value == 24.7` (unchanged from 0018), **and**
       `dateLastValueReported` updated to a UTC timestamp ≥ the
       publish moment;
    2. `GET /api/v1/devices/{id}/telemetry?controlledProperty=<attr>`
       returning at least one entry with `numValue == 24.7` and a
       `dateObserved` ≥ the publish moment;
    3. The corresponding entity
       `urn:ngsi-ld:DeviceMeasurement:<deviceUuid>:<Attr>` exists in
       Orion with `type == "DeviceMeasurement"`,
       `refDevice == <deviceUrn>`, `controlledProperty == <attr>` and
       `numValue == 24.7`.
- [ ] Publishing again on the same topic (same device + same `attr`)
      **updates** the existing `DeviceMeasurement` entity (no
      duplicate-id error from Orion); the next `/telemetry` call
      shows ≥ 2 entries for that `controlledProperty`.
- [ ] Publishing a non-numeric value (`Boolean` or `Text` per
      `dataTypes`) still updates `/state` (as in 0018) but does
      **not** create or modify any `DeviceMeasurement` entity. The
      `dropped_invalid` counter does not increment for this case.
- [ ] An invalid payload (bad JSON, oversized, `dataTypes` mismatch)
      still drops as in 0018: no Device patch, no Measurement upsert,
      `dropped_invalid` increments.

### B. Tests
- [ ] One new integration test in
      `platform/api/tests/test_mqtt_bridge.py` covering criterion A
      points 1–3 in a single publish, named
      `test_publish_lands_in_state_and_telemetry`.
- [ ] One new integration test asserting that two publishes on the
      same `<root>/<attr>` produce ≥ 2 telemetry entries (no upsert
      collision).
- [ ] One new integration test asserting that a Boolean publish
      updates `/state` but yields **no** `DeviceMeasurement` entity
      in Orion.
- [ ] `make test` stays green (~170 → ~173 tests).

### C. Code shape
- [ ] The canonical writer is a single async helper inside
      `mqtt_bridge.py` (or extracted to `mqtt_ingest.py` if it grows
      past ~30 lines), so 0019 can call it directly without
      duplicating the upsert logic.
- [ ] No new public route. No data-model change (the
      `DeviceMeasurement` schema is already pinned in
      `agent-workflow/data-model.md` and used by
      `platform/scripts/add_test_data.py`).
- [ ] `architecture.md` "Ingestion (current)" subsection is updated
      to reflect the new behaviour and to remove the "0018b is
      pending" caveat.

## Out of scope

- HTTP / LoRaWAN webhook ingest (0019). 0018b only fixes MQTT; the
  helper is shaped so 0019 can reuse it.
- `unitCode` resolution. The data model marks `unitCode` optional
  and 0018b ships it omitted; a follow-up ticket can map
  `controlledProperty → unitCode` (the `add_test_data.py` `UNITS`
  table is the obvious source).
- `textValue` for non-numeric measurements. Out of scope per
  `data-model.md` ("future ticket if needed").
- Backfilling existing `Device` rows in CrateDB. The historical 0018
  rows stay where they are; new publishes go to `DeviceMeasurement`.
- Any UI change. 0020 will surface the new data.

## Resolved decisions (user "all default" 2026-05-05)

- `unitCode` omitted on the upsert (optional in the data model).
- Measurement `dateObserved` is the bridge's UTC `datetime.now(...)`
  at message handling time, not a sensor-supplied timestamp. The
  payload wrapper does not yet carry a `ts` field; that is a future
  protocol extension.
- Upsert strategy: `POST /v2/entities` first, fall back to
  `POST /v2/entities/<id>/attrs` on `DuplicateEntity` (422 "Already
  Exists"). Mirrors `add_test_data.py`.
- Errors during the measurement upsert are logged at WARNING and do
  **not** roll back the Device patch — `/state` freshness is more
  important than telemetry consistency in v1.
