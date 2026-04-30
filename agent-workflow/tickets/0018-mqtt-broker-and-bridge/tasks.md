# Tasks — Ticket 0018 mqtt-broker-and-bridge

Goal: a real `paho-mqtt` publish lands in `/state` and CrateDB without
restarting anything.

## 1. Compose & broker config
- [ ] Add `mosquitto` service to `platform/compose/docker-compose.base.yml`
      (image `eclipse-mosquitto:2.0`, ports `127.0.0.1:${MQTT_PORT}:1883`,
      volumes for data/log/config). New named volumes
      `mosquitto_data`, `mosquitto_log`.
- [ ] Create `platform/config/mosquitto/mosquitto.conf` with listener
      1883, `allow_anonymous false`, `password_file
      /mosquitto/config/passwd`, persistence enabled.
- [ ] Add `mqtt-password` target to `Makefile` that regenerates
      `platform/config/mosquitto/passwd` from
      `MQTT_BRIDGE_USERNAME` / `MQTT_BRIDGE_PASSWORD` using
      `mosquitto_passwd -b -c`. Document in `make help`.
- [ ] Add `MQTT_PORT=1883`, `MQTT_BRIDGE_USERNAME=bridge`,
      `MQTT_BRIDGE_PASSWORD=change-me-bridge` to `platform/.env.example`
      and `platform/.env`.
- [ ] `.gitignore`: ignore `platform/config/mosquitto/passwd` (secret).
- [ ] Verify: `make up` and `mosquitto_pub -h localhost -p 1883 -u
      bridge -P change-me-bridge -t test/x -m '"hi"'` succeeds.

## 2. Backend: config & deps
- [ ] Add `paho-mqtt==2.1.0` to `platform/api/requirements.txt`.
- [ ] Extend `Settings` in `platform/api/app/config.py` with
      `mqtt_host`, `mqtt_port`, `mqtt_username`, `mqtt_password`,
      `mqtt_max_payload_bytes` (default 65536), `mqtt_enabled`
      (default True).

## 3. Payload helpers (pure)
- [ ] New `platform/api/app/mqtt_payload.py`:
      - `parse_payload(raw: bytes) -> Any` (strip wrapper `{"value":x}`,
        accept bare scalar, raise on non-JSON, raise if `> max`).
      - `infer_ngsi_type(value) -> tuple[str, Any]`.
      - `validate_against_dataTypes(attr, ngsi_type, value, dataTypes)
        -> bool`.
- [ ] New `platform/api/tests/test_mqtt_payload.py` with the 6 unit
      cases listed in `design.md` § Test strategy. Run isolated:
      `pytest tests/test_mqtt_payload.py -q`.

## 4. Bridge
- [ ] New `platform/api/app/mqtt_bridge.py`:
      - `MqttBridge` class wrapping `paho.mqtt.client.Client` in its
        own thread (`loop_start()`).
      - `start(loop, sessionmaker, orion_client)` — connects, subscribes
        to current MQTT devices.
      - `stop()` — disconnect + thread join.
      - `refresh()` — re-reads device list from Orion, diffs subs.
      - `stats()` — returns the dict for `/system/mqtt`.
      - `_on_message(client, userdata, msg)` — does payload parse,
        type infer, dataTypes validate, then schedules
        `orion.patch_entity(...)` via
        `asyncio.run_coroutine_threadsafe(coro, self._loop)`.
      - Counters: `last_message_at`, `dropped_invalid`,
        `subscribed_topics`, `connected`. In-flight cap 256.
      - Drop reasons logged at WARNING with one line each.

## 5. Wiring
- [ ] In `platform/api/app/main.py` `lifespan`: instantiate
      `MqttBridge(settings)`, `await bridge.start(loop, sessionmaker,
      orion)` after the Orion client is set up. Stash on
      `app.state.mqtt_bridge`. `await bridge.stop()` in `finally`.
      Skip if `settings.mqtt_enabled is False`.
- [ ] In `platform/api/app/routes/devices.py`: after every successful
      mutation (POST / PATCH / DELETE) call
      `request.app.state.mqtt_bridge.refresh()` inside a
      `try/except Exception: log` block (fire-and-forget).

## 6. New endpoint
- [ ] New `platform/api/app/routes/system.py` exposing
      `GET /system/mqtt` protected by `require_roles()` (admin-only).
- [ ] Mount in `main.py` with `settings.api_prefix`.

## 7. Integration tests
- [ ] In `platform/api/tests/conftest.py` add:
      - `mqtt_client` fixture: paho client connected with bridge creds,
        cleaned up on teardown.
      - `wait_until(predicate, timeout=5.0, interval=0.1)` helper.
- [ ] New `platform/api/tests/test_mqtt_bridge.py` with the 7
      integration cases in `design.md` § Test strategy.

## 8. Verify
- [ ] `make test` green (existing 145 + new ~13).
- [ ] Manual smoke:
      `mosquitto_pub` → `curl /devices/<id>/state` shows the value.
- [ ] Update `journal.md` with decisions taken during implementation
      and any deviations from the design.
- [ ] Update `review.md` self-review section.
- [ ] Flip `status.md` to `done`, set `closed:` date.
- [ ] One commit titled
      `feat(0018): MQTT broker + in-process bridge to Orion`.
