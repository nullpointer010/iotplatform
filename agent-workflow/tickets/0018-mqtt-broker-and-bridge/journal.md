# Journal — 0018 mqtt-broker-and-bridge

## 2026-05-01 — Implementation

**What landed**

- Mosquitto v2 added to Compose with password-file auth, persistence on,
  no anonymous, no TLS. Listener bound to `127.0.0.1:${MQTT_PORT}`.
- `make mqtt-password` regenerates the password file from
  `MQTT_BRIDGE_USERNAME` / `MQTT_BRIDGE_PASSWORD` via a one-shot
  `eclipse-mosquitto:2.0` container. `make up` calls it once if the
  password file is missing.
- `MqttBridge` runs in-process inside the FastAPI lifespan. Paho client
  in its own thread; Orion forwards hop back to the asyncio loop via
  `run_coroutine_threadsafe`.
- New `GET /api/v1/system/mqtt` (admin-only) returning
  `{connected, subscribed_topics, last_message_at, dropped_invalid}`.
- `routes/devices.py` fires `bridge.refresh()` after every successful
  POST/PATCH/DELETE.
- `StateResponse` extended with optional `attributes: dict[str,
  {type,value}]` so MQTT-pushed attributes appear in `/state` next to
  the existing `deviceState` / `dateLastValueReported` / `batteryLevel`
  triple.
- 16 unit tests on `mqtt_payload` + 7 integration tests on the bridge
  (paho publish → `/state` + RBAC).

**Decisions taken during implementation**

- *Topic shape*: settled on `<root>/<attr>` per attribute, with a
  `{"value": <x>}` wrapper or a bare scalar payload accepted. JSON-on-
  root rejected (no clean way to also carry timestamp/unit).
- *Numeric coercion*: int published into a Number slot is upcast to
  float; bool stays a Boolean (not a Number); string numerals are
  rejected.
- *Wildcard depth*: kept `<root>/+` (one level). Multi-level deferred
  to a follow-up if a real sensor demands it.
- *Bridge placement*: in-process, single deployable. A separate
  `iot-mqtt-bridge` container would have required RPC for refresh.
- *State vs telemetry split*: I added `attributes` onto `StateResponse`
  rather than a new endpoint, so existing UI consumers that already
  call `/state` get the new values for free.

**Deviations from `design.md`**

- Refresh trigger is `asyncio.create_task(bridge.refresh())` from the
  request handler, not a direct method call. `refresh()` is async (it
  reads Orion via `httpx.AsyncClient`), so we cannot block the request
  thread on it.
- I added an `_INFLIGHT_CAP = 256` short-circuit in `_on_message` to
  drop messages once the asyncio loop falls behind. The drop counts
  toward `dropped_invalid` (the same counter the spec lists for "drop
  reasons"). Documented in the design and surfaced in the new endpoint.

**Gotchas**

- `eclipse-mosquitto:2.0` warns on world-readable password files but
  still loads them. `make mqtt-password` chmods to 0644 after
  `mosquitto_passwd -c` so the file stays readable from the bind mount
  without needing host-side `mosquitto` user. Future ticket can switch
  to a docker secret.
- Mosquitto's container entrypoint tries to `chown` the config dir; the
  `:ro` mount makes that fail noisily, but it's a warning, not fatal.
- One pre-existing test (`test_query_lastN_limits_results`) is flaky
  under load — passes in isolation. Unrelated to this ticket.

**Manual smoke**

```bash
make up
TOKEN=$(curl -s -X POST 'http://localhost:8081/realms/iot-platform/protocol/openid-connect/token' \
  -d 'grant_type=password&client_id=iot-web&client_secret=dev-iot-web-secret' \
  -d 'username=admin&password=change-me-admin&scope=openid' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl -s -H "Authorization: Bearer $TOKEN" http://localhost/api/v1/system/mqtt
# → {"connected":true,"subscribed_topics":N,"last_message_at":...,"dropped_invalid":0}
```
