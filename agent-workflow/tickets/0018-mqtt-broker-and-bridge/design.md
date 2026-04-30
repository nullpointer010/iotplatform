# Design — Ticket 0018 mqtt-broker-and-bridge

## Approach

Add **Eclipse Mosquitto** as a sibling service to Orion / QL / Crate
on the existing `iot-net` network, password-file auth (no anonymous,
no TLS in dev). One Mosquitto user `bridge` is provisioned at
container start from env vars; sensors will get their own users in a
later operability ticket — for v1 the bridge is the only authenticated
client we care about.

The **bridge** is an in-process FastAPI background task started from
`lifespan` (rejected dedicated container, see Alternatives). On
startup it loads every device whose `supportedProtocol == "mqtt"` and
`mqttTopicRoot` is set, opens a single `paho.mqtt.client` connection
to `mosquitto:1883`, and subscribes to each `<root>/+`. On every
received message it parses the JSON payload, infers the NGSI v2 type
(`Number` / `Boolean` / `Text` / `StructuredValue`), validates it
against `dataTypes[topic_attr]` if present, and PATCHes the matching
attribute on `Device:<id>` via the existing `OrionClient.patch_entity`
— so the QL → Crate fan-out keeps working unchanged.

Subscription churn is handled by a **resubscribe trigger**: the
`devices` router emits a `bridge.refresh()` call on every successful
create / patch / delete. The bridge is a singleton on
`app.state.mqtt_bridge`, so the trigger is just an in-process method
call — no event bus, no Redis. We accept that subscription updates
are bound to API uptime; if the API is down, the broker buffers
nothing for us and we lose messages (documented constraint, matches
the requirements' "best-effort on restart" line).

## Open-question resolutions (from requirements)

1. **Topic shape**: per-attribute subtopic. `<mqttTopicRoot>/<attr>`.
   The last segment of the topic is the attribute name on the device.
   JSON-object-on-root is rejected because it requires a side-channel
   for which key is the timestamp / value / unit.
2. **Numeric coercion**: int → float is **accepted and cast**.
   bool → number is **rejected** (would mask a real schema mismatch).
   String numerals (`"42"`) are **rejected**: payload type wins.
3. **Wildcard depth**: one level (`/+`). Multi-level (`/#`) deferred.
4. **Bridge placement**: in-process background task. Single log
   stream, shared config, shared DB session. A separate container
   would force RPC for the resubscribe trigger and double the ops
   surface.

## Alternatives considered

- **A) Dedicated `iot-mqtt-bridge` container.** Rejected: would
  require either a Redis pub/sub or a polling re-fetch loop to learn
  about subscription changes; doubles the deployable units; gains
  no isolation that matters in dev. Easy to extract later if scaling
  requires it.
- **B) Use Orion IoT Agents (e.g. `iotagent-json`).** Rejected: heavy
  service, opinionated about provisioning model, would re-introduce
  a parallel device registry on top of our own. We stay closer to
  the spec (`backend.md`) which lists FIWARE Orion + QL but **not**
  IoT Agents.
- **C) Have sensors PATCH Orion directly.** Rejected: leaks the
  internal context broker to the field, forces every sensor firmware
  to learn NGSI v2, can't enforce `dataTypes`, no shared auth story.
- **D) Persist messages straight into CrateDB, bypass Orion.** Rejected:
  bypasses the spec's QL persistence path, loses the "current state"
  view that powers `/devices/{id}/state`, breaks subscriptions other
  components might add later.

## Affected files / new files

### Compose / config

- `platform/compose/docker-compose.base.yml` — new `mosquitto` service
  (image `eclipse-mosquitto:2.0`), bind on
  `127.0.0.1:${MQTT_PORT}:1883`, named volumes `mosquitto_data` and
  `mosquitto_log`, mount `../config/mosquitto:/mosquitto/config:ro`.
- `platform/.env.example` — add `MQTT_PORT=1883`,
  `MQTT_BRIDGE_USERNAME=bridge`,
  `MQTT_BRIDGE_PASSWORD=change-me-bridge`.
- `platform/config/mosquitto/mosquitto.conf` *(new)* — listener 1883,
  `allow_anonymous false`, `password_file /mosquitto/config/passwd`,
  `persistence true`, `persistence_location /mosquitto/data/`.
- `platform/config/mosquitto/passwd` *(new, generated)* — created
  once via a `make mqtt-password` target so it's reproducible from
  env vars and not committed plaintext.
- `Makefile` — add `mqtt-password` (regenerates `passwd` from env),
  document `MQTT_PORT` in `make help`.

### API

- `platform/api/requirements.txt` — add `paho-mqtt==2.1.0`
  (already pinned in the wider FIWARE ecosystem; pure-Python).
- `platform/api/app/config.py` — add `mqtt_host` (default
  `mosquitto`), `mqtt_port` (1883), `mqtt_username`, `mqtt_password`,
  `mqtt_max_payload_bytes` (default `65536`), `mqtt_enabled`
  (default `True`, set `False` in some integration tests if needed).
- `platform/api/app/mqtt_bridge.py` *(new)* — `MqttBridge` class:
  `start()`, `stop()`, `refresh()`, `stats()`. Wraps `paho-mqtt` in
  its own threaded loop; communicates with the asyncio side via
  `asyncio.run_coroutine_threadsafe` to call `OrionClient.patch_entity`.
  Holds counters (`connected`, `subscribed_topics`, `dropped_invalid`,
  `last_message_at`).
- `platform/api/app/mqtt_payload.py` *(new)* — pure helpers:
  `infer_ngsi_type(value) -> (ngsi_type, value)`,
  `validate_against_dataTypes(attr, value, dataTypes) -> bool`. Unit
  testable without a broker.
- `platform/api/app/main.py` — instantiate `MqttBridge` after Orion
  client, `await bridge.start()` inside `lifespan`, `await bridge.stop()`
  in the `finally` block. Skip when `settings.mqtt_enabled` is False.
- `platform/api/app/routes/devices.py` — call
  `app.state.mqtt_bridge.refresh()` (best-effort, swallow on error)
  after successful create / patch / delete of an MQTT device. Pure
  fire-and-forget; doesn't change any HTTP response code.
- `platform/api/app/routes/system.py` *(new)* — `GET /system/mqtt`
  (admin-only via `require_roles()`) returns the bridge stats. The
  router is mounted at `settings.api_prefix`.

### Tests

- `platform/api/tests/test_mqtt_payload.py` *(new)* — pure unit tests
  for the type-inference + validation helpers. No broker needed.
- `platform/api/tests/test_mqtt_bridge.py` *(new)* — integration:
  publish via `paho-mqtt` to `localhost:${MQTT_PORT}` after creating
  an MQTT device with `mqttTopicRoot=test/<uuid>` and `dataTypes={
  "temp": "Number" }`, then assert the value appears in Orion within
  2 s and a CrateDB row exists within 5 s. Reuses the existing
  `api` / `tokens` / `created_ids` fixtures; needs a new
  `mqtt_client` fixture in `conftest.py`.
- `platform/api/tests/conftest.py` — `mqtt_client` fixture (paho
  client connected with bridge creds), helper to wait for a Crate
  row by `entity_id`. No new TRUNCATE entries; nothing persisted in
  Postgres.

## Data model / API contract changes

- **No schema changes.** Bridge piggybacks on the existing `Device`
  entity in Orion and the `dataTypes` attribute we already accept.
- **One new endpoint**: `GET /api/v1/system/mqtt` — admin-only.

  Response shape:
  ```json
  {
    "connected": true,
    "subscribed_topics": 23,
    "last_message_at": "2026-05-01T10:42:13Z",
    "dropped_invalid": 4
  }
  ```

- **Side effect on existing endpoints**: `POST/PATCH/DELETE /devices`
  now triggers a non-blocking `bridge.refresh()`. No change to HTTP
  status codes or response bodies.

## Topic / payload contract (sensor-facing)

For an MQTT device with `id=<uuid>`,
`mqttTopicRoot=crop/almeria/dev007`, `dataTypes={"temp":"Number",
"door":"Boolean"}`:

```text
crop/almeria/dev007/temp     ← {"value": 24.7}            → Device:<uuid>.temp = 24.7 (Number)
crop/almeria/dev007/door     ← {"value": false}           → Device:<uuid>.door = false (Boolean)
crop/almeria/dev007/extra    ← {"value": {"a":1,"b":2}}   → Device:<uuid>.extra = {...} (StructuredValue)
```

Accepted shorthand: a bare scalar payload (`24.7`) is treated as
`{"value": 24.7}`. JSON wins over content-type. No QoS upgrade —
QoS 0 on the bridge subscriber for v1 (we don't claim durability).

## Risks

- **Broker availability coupling.** If Mosquitto is down, the bridge
  reconnects with backoff; nothing else in the API breaks. Mitigated
  by paho's auto-reconnect + a watchdog log line every 30 s while
  disconnected.
- **Hot-reload race.** A `bridge.refresh()` triggered by a `DELETE
  /devices/{id}` while a message for the same device is in flight
  could PATCH a deleted entity. Orion answers `404`; we log and drop.
- **Backpressure.** The asyncio→paho thread bridges every message
  through `run_coroutine_threadsafe`. Under load this can pile up
  on the loop. We measure this in 0026 (system-health-page); for
  this ticket we just drop with a counter once the in-flight count
  passes a small cap (`MQTT_INFLIGHT_CAP = 256`).
- **Auth blast radius.** One shared `bridge` user is the broker's
  only authenticated client. If its password leaks, an attacker can
  publish on any topic. Acceptable in dev; per-device ACLs and TLS
  are explicitly deferred (see Out of scope).
- **Test flake.** Cross-service timing (paho → Mosquitto → bridge →
  Orion → QL → Crate) can race. Mitigated with a polling assertion
  helper (`wait_until` with 5 s timeout) instead of fixed sleeps.

## Test strategy for this ticket

- **Unit** (`test_mqtt_payload.py`):
  - `infer_ngsi_type(24)` → `("Number", 24.0)` (int → float cast).
  - `infer_ngsi_type(True)` → `("Boolean", True)` (bool not Number).
  - `infer_ngsi_type({"a":1})` → `("StructuredValue", {"a":1})`.
  - `validate_against_dataTypes("temp", 24.0, {"temp":"Number"})` → True.
  - `validate_against_dataTypes("door", 1.0, {"door":"Boolean"})` → False.
  - `validate_against_dataTypes("temp", "42", {"temp":"Number"})` → False.

- **Integration** (`test_mqtt_bridge.py`, runs inside the existing
  Compose-stack-based suite):
  - `test_mqtt_publish_lands_in_orion`: create device → publish →
    poll `/state` until present (`< 2 s`).
  - `test_mqtt_publish_lands_in_crate`: same, then poll Crate via
    QuantumLeap-aware fixture (`< 5 s`).
  - `test_mqtt_invalid_json_dropped`: publish `not-json`, assert
    `dropped_invalid` increments and no `/state` change.
  - `test_mqtt_dataTypes_mismatch_dropped`: device with
    `dataTypes={"temp":"Number"}`, publish `{"value":"hi"}`, assert
    drop counter +1.
  - `test_mqtt_subscription_refresh_on_create`: connect bridge,
    create a fresh MQTT device, publish — value must land without
    restart.
  - `test_mqtt_subscription_refresh_on_delete`: delete the device,
    publish on its old root, assert no `Device:<id>` in Orion (404).
  - `test_system_mqtt_endpoint_admin_only`: 200 for admin, 403 for
    operator/manager/viewer, 401 for anon.

- **Manual verification** (documented in journal at close):
  ```bash
  make up
  # Register an MQTT device
  curl -u admin:change-me-admin -X POST http://localhost/api/v1/devices \
       -H 'content-type: application/json' \
       -d '{"id":"...","category":"sensor","supportedProtocol":"mqtt",
            "name":"demo","mqttTopicRoot":"crop/test/demo",
            "mqttClientId":"demo","dataTypes":{"temp":"Number"}}'
  mosquitto_pub -h localhost -p 1883 -u bridge -P change-me-bridge \
                -t crop/test/demo/temp -m '{"value":24.7}'
  # Wait ~1 s
  curl -u admin:change-me-admin http://localhost/api/v1/devices/<id>/state
  # → temp: 24.7
  ```
