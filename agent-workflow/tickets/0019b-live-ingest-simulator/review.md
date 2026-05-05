# Review — Ticket 0019b

## What changed

New:
- `platform/api/app/simulator.py` — `LiveSimulator` background task.
  Each tick walks all devices in Orion and:
  - publishes MQTT for `mqtt` devices (real paho client),
  - HTTP-POSTs for `http` devices via real loopback to
    `/api/v1/devices/{id}/telemetry`,
  - flips other-protocol devices to `deviceState=maintenance`
    (one-shot PATCH).
  Also deletes legacy `[demo] …` entities created by the v1 of
  this module.

Modified:
- `platform/api/app/main.py` — start/stop simulator from lifespan,
  pass it the MQTT bridge so it can `refresh()` after bootstrap.
- `platform/api/app/config.py` — `simulator_enabled` (default off
  in Settings), `simulator_interval_seconds` (default 10),
  `simulator_api_base_url` (default `http://localhost:8000`).
- `platform/compose/docker-compose.api.yml` — `SIMULATOR_ENABLED`
  defaults to `true` for `make up`.

## Acceptance criteria — evidence

- **A.1** Simulator never calls `create_entity`. Verified: device
  count after `make up` matches whatever was in Orion before.
- **A.2** After 30 s, all 30 MQTT/HTTP devices in the seed fleet
  show a fresh `dateLastValueReported`.
- **A.3** Code path: `_ensure_http_key` only inserts/rotates rows
  when `existing is None or existing.created_by == "simulator"`;
  otherwise the device is added to `_http_skip` and ignored.
- **A.4** All 22 lorawan/plc/modbus devices end up in
  `deviceState=maintenance`. One-shot via `_maintenance_done` set.
- **A.5** `make test` → 183/183 passed.
- **A.6** Legacy `[demo] …` URNs deleted at startup. Verified
  count = 0.

## Follow-ups

- **FU1** Native ingestion adapters for LoRaWAN (Chirpstack/TTN
  webhook → `apply_measurement`), CoAP, Sigfox. Once an adapter
  lands, drop the protocol from the maintenance-set in this file.
- **FU2** Optional `/system/simulator` endpoint to start/stop /
  set the interval at runtime, only if it actually helps demos.
- **FU3** Consider gating `make test` to set `SIMULATOR_ENABLED=false`
  in the test container env, to remove residual concurrency between
  the simulator and integration tests.
- **FU4** When 0020 ships the `dataTypes` editor, pick a richer
  set of `controlledProperty` values (windSpeed, soilMoisture,
  pressure, …); ranges already in `_RANGES`.

## Self-review notes

- The simulator never reverts a device to `active`. If the user
  manually flips a maintenance device to `active`, on the next tick
  it would be flipped back — but only if it's still on a non-live
  transport. Acceptable: changing transport is a real operator
  action and would re-trigger.
- Random-walk values are independent per `(device, attr)`; they
  drift but stay bounded. No cross-device correlation.
- HTTP loopback URL is hard-coded in env to `http://localhost:8000`
  (the uvicorn bind inside the iot-api container). Outside the
  container the env var would need to point at the API gateway.
