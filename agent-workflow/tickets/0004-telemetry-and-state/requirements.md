# 0004 — telemetry-and-state

## Why

`backend.md` defines `GET /api/v1/devices/{id}/telemetry` as the single
read path for time-series data. The roadmap also pins
`GET /api/v1/devices/{id}/state` as a thin convenience endpoint exposing
the operational subset of the Device entity. With ticket 0003 we can
register devices but not query their measurements; closing this ticket
unlocks the dashboard work in 0007.

## What

Two new endpoints on the existing `iot-api` service:

1. `GET /api/v1/devices/{id}/telemetry` — proxies QuantumLeap. The
   measurement entity convention from `data-model.md` is
   `urn:ngsi-ld:DeviceMeasurement:<deviceUuid>:<controlledProperty>`.
2. `GET /api/v1/devices/{id}/state` — returns the operational subset of
   the Device entity from Orion (`deviceState`, `dateLastValueReported`,
   `batteryLevel`).

A QuantumLeap async HTTP client is added alongside the existing Orion
client. The Orion → QuantumLeap subscription registered in 0001 already
covers any entity (`idPattern: ".*"`), so `DeviceMeasurement` entities
flow through to CrateDB without further wiring.

## Acceptance criteria

1. `GET /devices/{id}/telemetry?controlledProperty=temperature` returns
   `200` with `{deviceId, controlledProperty, entries: [{dateObserved,
   numValue, unitCode?}]}` for a device that has emitted measurements.
2. Same call against an existing device with no measurements returns
   `200` with `entries: []` (empty range, not 404).
3. Unknown device id (Orion) → `404`.
4. Missing `controlledProperty` query param → `422`.
5. `fromDate > toDate` → `400`.
6. Invalid ISO-8601 in `fromDate` / `toDate` → `422` (FastAPI/Pydantic
   datetime validation).
7. `lastN`, `limit`, `offset` validated as positive ints with the same
   bounds as devices listing (`1–1000`, `0+`).
8. `GET /devices/{id}/state` returns `200` with
   `{deviceState?, dateLastValueReported?, batteryLevel?}`. Fields absent
   from the entity are omitted from the response.
9. `GET /devices/{id}/state` for an unknown device → `404`.
10. End-to-end ingestion verified: a test pushes a `DeviceMeasurement`
    via Orion, polls the API until QuantumLeap has indexed it, and
    asserts the values round-trip.
11. `make test` runs the full suite (devices + telemetry + state) green.

## Out of scope

- Multi-property aggregation (returning all `controlledProperty` series
  in one call).
- Non-numeric measurement attributes (`textValue`).
- CrateDB monthly partitioning DDL — see journal: CrateDB requires
  `PARTITIONED BY` at `CREATE TABLE`, not via `ALTER TABLE`, so the DDL
  pinned in `data-model.md` does not apply as-written. Deferred to a
  later operations ticket that will pre-create the QL table or migrate
  it.
- Authentication / RBAC (ticket 0009).
- Realtime push / WebSocket / SSE (Phase 2).

## Open questions

None blocking.
