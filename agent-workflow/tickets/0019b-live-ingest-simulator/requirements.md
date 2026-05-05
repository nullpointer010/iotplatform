# Requirements — Live Ingest Simulator

## Problem
After 0018/0018b/0019, the platform supports live ingestion via MQTT
and HTTP, but a freshly-started stack (`make up`) shows nothing
moving. The user has to manually publish messages or curl the ingest
endpoint to see telemetry come alive. That's friction for demos and
ongoing development.

## Goal
After `make up`, the stack continuously ingests realistic telemetry
through **both** real ingestion paths (MQTT broker + HTTP `/telemetry`
route) without any extra command, so the UI's `/state`, `/telemetry`,
charts and floorplan overlays show live activity.

## In scope
- 5 demo devices auto-provisioned in Orion at startup (3 MQTT-protocol,
  2 HTTP-protocol). Idempotent: re-running `make up` does not duplicate.
- Background task in `iot-api` that publishes a measurement per attribute
  every ~10 s for each demo device, via the protocol the device declares.
- MQTT path: real `paho` PUBLISH to Mosquitto using the bridge's
  credentials. Goes through the existing bridge → canonical writer.
- HTTP path: real HTTP POST to `http://localhost:8000/api/v1/devices/{id}/telemetry`
  with a per-device `X-Device-Key`. The simulator owns these keys
  (`created_by="simulator"`); it never overwrites operator-issued keys.
- Gated by `SIMULATOR_ENABLED` env var (default `false` in `Settings`,
  default `true` in compose).

## Out of scope
- Other transports (PLC, LoRaWAN, Modbus). Skipped with a log line;
  tracked under the existing roadmap item for protocol simulators.
- A user-facing UI to start/stop the simulator.
- Determinism — values are random walks, not replayable traces.

## User stories
- *As a developer*, when I `make up`, within ~30 s the dashboard shows
  several devices reporting fresh values that change over time.
- *As a tester*, I can disable the simulator (`SIMULATOR_ENABLED=false`)
  to get a quiet stack for assertions.

## Acceptance criteria
- A.1 With `SIMULATOR_ENABLED=true`, a fresh stack auto-creates exactly
  5 demo devices visible in `GET /api/v1/devices`, named `[demo] …`.
- A.2 Within 30 s of stack-up, `GET /api/v1/devices/{id}/state` for a
  demo MQTT device shows non-null values and a recent
  `dateLastValueReported`.
- A.3 Same for an HTTP demo device, but its `device_ingest_keys` row
  has `created_by="simulator"`.
- A.4 `GET /api/v1/devices/{id}/telemetry?controlledProperty=temperature`
  returns ≥ 2 entries within ~30 s for any demo device.
- A.5 Existing tests pass unchanged. Simulator is off by default in
  Settings; tests don't enable it.
- A.6 Simulator never rotates keys whose `created_by != "simulator"`.

## Resolved decisions
- In-process inside `iot-api`, not a separate container. One less moving
  part; reuses `OrionClient`, sessionmaker, and lifespan.
- Demo devices use a fixed UUIDv5 namespace so re-runs of `make up`
  hit the same URNs (idempotent).
- HTTP path uses real loopback HTTP (`httpx → localhost:8000`), not a
  direct call to `apply_measurement`, so the actual route + auth +
  validation are exercised continuously.
