# Tasks — Ticket 0018 mqtt-broker-and-bridge

Goal: a real `paho-mqtt` publish lands in `/state` and CrateDB without
restarting anything.

> **2026-05-05 reconciliation (ticket 0018a):** all checkboxes below
> reflect what was actually delivered and is in `main`. The implicit
> promise that *"a publish appears in `/api/v1/devices/{id}/telemetry`"*
> was **not** met — the bridge updates the `Device` entity, but
> `/telemetry` reads `DeviceMeasurement` entities. That work is
> **moved to 0018b telemetry-ingest-canonicalization**.

## 1. Compose & broker config
- [x] Add `mosquitto` service to `platform/compose/docker-compose.base.yml`
      (image `eclipse-mosquitto:2.0`, ports `127.0.0.1:${MQTT_PORT}:1883`,
      volumes for data/log/config). New named volumes
      `mosquitto_data`, `mosquitto_log`.
- [x] Create `platform/config/mosquitto/mosquitto.conf` with listener
      1883, `allow_anonymous false`, `password_file
      /mosquitto/config/passwd`, persistence enabled.
- [x] Add `mqtt-password` target to `Makefile` that regenerates
      `platform/config/mosquitto/passwd` from
      `MQTT_BRIDGE_USERNAME` / `MQTT_BRIDGE_PASSWORD` using
      `mosquitto_passwd -b -c`. Document in `make help`.
- [x] Add `MQTT_PORT=1883`, `MQTT_BRIDGE_USERNAME=bridge`,
      `MQTT_BRIDGE_PASSWORD=change-me-bridge` to `platform/.env.example`
      and `platform/.env`.
- [x] `.gitignore`: ignore `platform/config/mosquitto/passwd` (secret).
- [x] Verify: `make up` and `mosquitto_pub -h localhost -p 1883 -u
      bridge -P change-me-bridge -t test/x -m '"hi"'` succeeds.

## 2. Backend: config & deps
- [x] Add `paho-mqtt==2.1.0` to `platform/api/requirements.txt`.
- [x] Extend `Settings` in `platform/api/app/config.py` with
      `mqtt_host`, `mqtt_port`, `mqtt_username`, `mqtt_password`,
      `mqtt_max_payload_bytes` (default 65536), `mqtt_enabled`
      (default True).

## 3. Payload helpers (pure)
- [x] New `platform/api/app/mqtt_payload.py`:
      - `parse_payload(raw: bytes) -> Any` (strip wrapper `{"value":x}`,
        accept bare scalar, raise on non-JSON, raise if `> max`).
      - `infer_ngsi_type(value) -> tuple[str, Any]`.
      - `validate_against_dataTypes(attr, ngsi_type, value, dataTypes)
        -> bool`.
- [x] New `platform/api/tests/test_mqtt_payload.py` with the unit
      cases (16 in delivered code, vs 6 originally planned).

## 4. Bridge
- [x] New `platform/api/app/mqtt_bridge.py`:
      - `MqttBridge` class wrapping `paho.mqtt.client.Client` in its
        own thread (`loop_start()`).
      - `start(loop, orion_client)` — connects, subscribes
        to current MQTT devices. *(No `sessionmaker` needed in the
        delivered design; subs come from Orion.)*
      - `stop()` — disconnect + thread join.
      - `refresh()` — re-reads device list from Orion, diffs subs.
      - `stats()` — returns the dict for `/system/mqtt`.
      - `_on_message(client, userdata, msg)` — does payload parse,
        type infer, dataTypes validate, then schedules
        `orion.patch_entity(...)` via
        `asyncio.run_coroutine_threadsafe(coro, self._loop)`.
        **Note:** patches the `Device` entity; does **not** create
        a `DeviceMeasurement` (→ 0018b).
      - Counters: `last_message_at`, `dropped_invalid`,
        `subscribed_topics`, `connected`. In-flight cap 256.
      - Drop reasons logged at WARNING with one line each.

## 5. Wiring
- [x] In `platform/api/app/main.py` `lifespan`: instantiate
      `MqttBridge(settings)`, `await bridge.start(loop, orion)` after
      the Orion client is set up. Stash on `app.state.mqtt_bridge`.
      `await bridge.stop()` in `finally`. Skip if
      `settings.mqtt_enabled is False`.
- [x] In `platform/api/app/routes/devices.py`: after every successful
      mutation (POST / PATCH / DELETE) call
      `request.app.state.mqtt_bridge.refresh()` inside a
      `try/except Exception: log` block (fire-and-forget).

## 6. New endpoint
- [x] New `platform/api/app/routes/system.py` exposing
      `GET /system/mqtt` protected by `require_roles()` (admin-only).
- [x] Mount in `main.py` with `settings.api_prefix`.

## 7. Integration tests
- [x] `mqtt_client` fixture + `_wait_until` helper. *(Delivered
      inline in `tests/test_mqtt_bridge.py` instead of `conftest.py`;
      functionally equivalent.)*
- [x] New `platform/api/tests/test_mqtt_bridge.py` with 7
      integration cases.

## 8. Verify
- [x] `make test` green.
- [x] Manual smoke: `mosquitto_pub` → `curl /devices/<id>/state`
      shows the value.
- [ ] Manual smoke: `mosquitto_pub` → `curl /devices/<id>/telemetry`
      shows the value. **→ moved to 0018b** (requires
      `DeviceMeasurement` upsert).
- [x] Update `journal.md` with decisions taken during implementation
      and any deviations from the design. *(Backfilled 2026-05-05 in
      ticket 0018a.)*
- [x] Update `review.md` self-review section. *(Backfilled
      2026-05-05 in ticket 0018a.)*
- [x] Flip `status.md` to `done`, set `closed:` date.
- [x] One commit titled
      `feat(0018): MQTT broker + in-process bridge to Orion`.
