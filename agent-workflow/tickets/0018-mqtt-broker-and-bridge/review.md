# Review — 0018 mqtt-broker-and-bridge

## Acceptance criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Mosquitto in Compose, configurable port, password auth | ✅ | `platform/compose/docker-compose.base.yml`, `platform/config/mosquitto/mosquitto.conf` |
| 2 | Bridge user provisioned from env | ✅ | `make mqtt-password` target |
| 3 | Bridge runs from FastAPI lifespan (in-process) | ✅ | `app/main.py` `lifespan` |
| 4 | Subscribes to `<mqttTopicRoot>/+` per device | ✅ | `MqttBridge._desired_subs`, `refresh()` |
| 5 | Routes last topic segment to one Orion attr | ✅ | `_handle_message` + `OrionClient.patch_entity` |
| 6 | Number/Boolean/Text/StructuredValue coercion | ✅ | `mqtt_payload.infer_ngsi_type` |
| 7 | `dataTypes` mismatch → drop + counter, no crash | ✅ | `validate_against_dataTypes`, `_drop` |
| 8 | Resubs within 5s on device CRUD | ✅ | `routes/devices.py` `_maybe_refresh_bridge` + `test_subscription_refresh_on_create` |
| 9 | Malformed JSON / unknown topic / oversized → single log line each | ✅ | `_drop` reasons in `mqtt_bridge.py` |
| 10 | `GET /system/mqtt` admin-only | ✅ | `routes/system.py` + `test_system_mqtt_endpoint_rbac` |
| 11 | Integration test: publish → state in <2s, Crate row <5s | ✅ | `test_publish_lands_in_state_and_crate` |
| 12 | No RBAC change for sensors | ✅ | Bridge auths to Mosquitto with shared `bridge` creds |
| 13 | `make test` stays green (modulo pre-existing flake) | ✅ | 167/168, sole failure is pre-existing telemetry race |

## Self-review

- **Security**: shared bridge user is plaintext over loopback only.
  Real sensor creds + ACLs are explicitly deferred to a later
  operability ticket. Password file is git-ignored. The new
  `/system/mqtt` endpoint is admin-only.
- **Backpressure**: 256-message inflight cap protects the asyncio loop.
  Documented in `journal.md`.
- **Tests**: 16 unit + 7 integration. Unit tests are pure (no broker
  dependency). Integration tests use `paho-mqtt` against the live
  Compose stack (same pattern as the rest of the suite).
- **Code style**: matches the existing module layout (helper module +
  bridge class + thin route wrapper).
- **Docs**: requirements / design / tasks / journal / review all
  filled. `roadmap.md` already lists 0019–0030 follow-ups.

## Follow-ups (deferred)

- 0019 http-ingest-endpoint — same idea but for HTTP/CoAP-shaped sensors.
- 0020 device-live-state-and-charts — wire the new `attributes` block
  into the device detail page.
- 0026 system-health-page — surface the `/system/mqtt` stats in the UI.
- 0027 backups-and-restore — Mosquitto persistence dir needs to be in
  the backup set.
- 0028 prod-edge-tls — TLS + per-device ACLs on Mosquitto.
