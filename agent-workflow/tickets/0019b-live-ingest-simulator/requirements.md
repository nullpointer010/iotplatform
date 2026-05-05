# Requirements — Live Ingest Simulator

## Problem
After 0018/0018b/0019, the platform supports live ingestion via MQTT
and HTTP, but a freshly-started stack (`make up`) shows nothing
moving. The user has to manually publish messages or curl the ingest
endpoint to see telemetry come alive. Synthetic seed devices (the
output of `make seed`) look real but stay silent.

## Goal
After `make up`, **every registered device** with a live transport
(MQTT or HTTP) continuously emits realistic telemetry through that
transport's real ingestion path. Devices on transports we don't
have an adapter for yet (LoRaWAN, PLC, Modbus, CoAP, …) are flipped
to `deviceState="maintenance"` so the UI honestly reflects that they
aren't reporting.

## In scope
- A background task in `iot-api`, gated by `SIMULATOR_ENABLED`.
- For every device with `supportedProtocol == "mqtt"`: publish a
  random-walk value per `controlledProperty` every ~10 s via paho
  to Mosquitto. The bridge → canonical writer takes it from there.
- For every device with `supportedProtocol == "http"`: real HTTP
  POST to `/api/v1/devices/{id}/telemetry` with a per-device
  `X-Device-Key` (auto-issued the first time the simulator sees
  the device; row labelled `created_by="simulator"`).
- For every device on any other transport: PATCH `deviceState` to
  `"maintenance"` once at startup. Idempotent.
- One-time cleanup of legacy demo devices created by an earlier
  version of this module (`[demo] MQTT/HTTP sensor 1..5`).

## Out of scope
- An ingestion adapter for LoRaWAN/PLC/Modbus/CoAP — tracked
  separately on the roadmap.
- A user-facing UI to start/stop the simulator.
- Replayable / deterministic data — values are independent random
  walks per `(device, attr)`.

## User stories
- *As a developer*, when I `make up`, within ~30 s every MQTT and
  HTTP device on the dashboard shows fresh values that change over
  time. Devices on other protocols sit visibly in maintenance.
- *As a tester*, I can disable the simulator (`SIMULATOR_ENABLED=false`)
  for a quiet stack.

## Acceptance criteria
- A.1 With `SIMULATOR_ENABLED=true`, the simulator does **not**
  create any device of its own — the device list comes from
  whatever's already in Orion (incl. `make seed`).
- A.2 Within 30 s of stack-up, every MQTT/HTTP device with a
  matching `mqttTopicRoot`/protocol has a non-null
  `dateLastValueReported` and at least one `controlledProperty`
  value populated.
- A.3 For every HTTP device the simulator publishes against, a
  `device_ingest_keys` row exists with `created_by="simulator"`.
  An operator-issued key (any other `created_by`) is never
  overwritten.
- A.4 Devices whose `supportedProtocol` is neither `mqtt` nor
  `http` end up at `deviceState="maintenance"` (one-shot PATCH).
- A.5 Existing tests pass. Simulator is off by default in `Settings`.
- A.6 The legacy `[demo] …` devices created by the previous
  version of this module are removed at startup.

## Resolved decisions
- In-process inside `iot-api`. Reuses `OrionClient`, sessionmaker,
  and lifespan. No extra container.
- HTTP path uses real loopback HTTP, not a direct call to
  `apply_measurement`, so the actual route + auth + validation are
  exercised continuously.
- The simulator does not create or seed devices — that's `make seed`'s
  job. The simulator only animates whatever is registered.
