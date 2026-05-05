# Review — Ticket 0019b

## What changed

New:
- `platform/api/app/simulator.py` — `LiveSimulator` background task
  that auto-creates 5 demo devices in Orion (3 MQTT + 2 HTTP) and
  publishes realistic random-walk telemetry through both real
  ingestion paths.

Modified:
- `platform/api/app/main.py` — start/stop simulator from lifespan,
  pass it the MQTT bridge so it can `refresh()` after bootstrap.
- `platform/api/app/config.py` — `simulator_enabled` (default off),
  `simulator_interval_seconds` (default 10), `simulator_api_base_url`
  (default `http://localhost:8000`).
- `platform/compose/docker-compose.api.yml` — new env vars,
  `SIMULATOR_ENABLED` defaults to `true` for `make up`.

## Acceptance criteria — evidence

- **A.1** `make up` then `curl /v2/entities?q=name~=demo` returns
  exactly 5 entities.
- **A.2** `[demo] MQTT sensor 1` shows live `temperature`,
  `humidity`, `dateLastValueReported` within ~10 s.
- **A.3** `[demo] HTTP sensor 4` likewise; the row in
  `device_ingest_keys` for it has `created_by='simulator'`.
- **A.4** `GET /v2/entities/urn:ngsi-ld:DeviceMeasurement:<uuid>:Temperature/attrs/numValue?lastN=5`
  on QuantumLeap returns ≥ 2 entries within ~30 s.
- **A.5** `make test` → 182 passed, 1 pre-existing flake unrelated.
- **A.6** Code path `_ensure_http_key` early-returns when
  `existing.created_by != "simulator"`.

## Follow-ups

- **FU1** Cover other transports (LoRaWAN webhook, CoAP) once those
  ingestion adapters land.
- **FU2** Optional `/system/simulator` endpoint to start/stop or set
  the interval at runtime — only if it actually helps demos.
- **FU3** Consider a `make demo` target that boots the stack with
  `SIMULATOR_ENABLED=true` and `make seed`, and a `make ci` that
  forces it off, instead of relying on the compose default.

## Self-review notes

- `_DEMO_NS` UUID was chosen with a "51ed" tail purely for grep-ability;
  no semantic meaning.
- `OrionClient.list_entities` is unused — we fetch each demo device
  individually by URN. Cheaper for 5 known IDs and avoids racing
  with mid-tick CRUD.
- The MQTT publisher is a separate paho client from the bridge, with
  its own client id (`iot-api-simulator`). Mosquitto handles the two
  client ids fine.
- Simulator `dataTypes` shape (`{"temperature":"Number"}` flat string)
  matches what the bridge enforces today. If 0020's `dataTypes` editor
  changes the wire format, both the editor and this file move together.
