# Journal — Ticket 0019b

## 2026-05-05 — v1: 5 demo devices
First cut bootstrapped 5 fixed demo devices (3 MQTT + 2 HTTP) with
UUIDv5 URNs and pumped telemetry into them. Worked, but the user
pointed out the obvious: the dashboard already has 50+ realistic
seed devices that stay silent, and the demo entries look
suspiciously synthetic next to them.

## 2026-05-05 — v2: animate every device
Pivot. The simulator no longer creates or seeds devices — that's
`make seed`'s job. Each tick:

1. List every device in Orion (`OrionClient.list_entities` paged).
2. For each:
   - `supportedProtocol == "mqtt"` → paho PUBLISH on
     `<mqttTopicRoot>/<attr>` for each `controlledProperty`. The
     bridge consumes and runs the canonical writer.
   - `supportedProtocol == "http"` → loopback HTTP POST to
     `/telemetry` with a simulator-owned `X-Device-Key`.
   - anything else → one-shot PATCH `deviceState=maintenance`.

Plus a one-time `_cleanup_legacy_demo_devices` step that deletes the
five `[demo] …` URNs from v1 if they're still around.

### Surprises
- `dataTypes` shape gotcha (carried from 0018b): the bridge enforces
  a flat `{attr: "Number"}` dict. Doesn't matter for the seed devices
  (they don't declare `dataTypes`), but worth noting for FU5 from 0019.
- The seed devices that were produced before this version landed
  already had varied `deviceState` values; PATCHing
  `deviceState=maintenance` for non-mqtt/http transports is mildly
  invasive but matches what the user explicitly asked for.
- Random walk uses the same per-attr ranges as `add_test_data.py`
  so the simulator's values look like the seed history did.

### Verified live
After `make up` and ~30 s the platform shows:
- 30 mqtt/http devices with fresh `dateLastValueReported` and live
  values.
- 22 lorawan/plc/modbus devices in `maintenance`.
- No `[demo] …` devices.
- `make test`: 183/183 (the previously-flaky telemetry test
  happened to pass too this run).

### Files touched
- new `platform/api/app/simulator.py` (~330 LOC)
- `platform/api/app/main.py` (lifespan wiring)
- `platform/api/app/config.py` (3 settings)
- `platform/compose/docker-compose.api.yml` (3 env vars)
- new ticket folder
