# Ticket 0018 — mqtt-broker-and-bridge

## Problem

After Phase 1 closed, the platform has a polished metadata catalog
(devices, manuals, floor plans, RBAC, i18n) but **no real telemetry
ingestion**: every measurement currently in CrateDB came from
`make seed` poking Orion directly. The `context/doc/backend.md` spec
itself flags MQTT/CoAP/HTTP ingestion as deferred. Without it, the
platform is a demo — no greenhouse sensor can publish a value.

## Goal

Add an in-network MQTT broker (Eclipse Mosquitto) and an in-process
**bridge** worker that subscribes to each registered MQTT device's
`mqttTopicRoot/+` and forwards every published message into Orion as
an attribute update on `Device:<id>`, so the existing Orion → QL →
CrateDB path persists it. With this ticket, a real sensor (or a
`paho-mqtt` test client) can publish a JSON value and see it appear
both in `GET /api/v1/devices/{id}/state` and in
`GET /api/v1/devices/{id}/telemetry`.

## User stories

- As an **operator**, when I register an MQTT device with
  `mqttTopicRoot=crop/almeria/dev007`, any JSON message published to
  `crop/almeria/dev007/<attr>` is automatically persisted as an
  attribute update on that device — without me restarting anything.
- As a **viewer**, the device detail "Estado" tab reflects the latest
  published value within seconds of it being received.
- As a **manager**, the historical chart in the "Telemetría" tab
  contains points from real MQTT publishes (not just seed data).
- As a **developer**, I can run `paho-mqtt` against
  `localhost:<MQTT_PORT>` with the seeded credentials and watch a
  CrateDB row appear inside an integration test.

## Acceptance criteria (verifiable)

- [ ] `make up` brings up a `mosquitto` service on a configurable host
  port `MQTT_PORT` (default `1883`), with persistence enabled and
  password-file auth (no anonymous, no TLS in dev).
- [ ] One Mosquitto user is provisioned at bootstrap from
  `MQTT_BRIDGE_USERNAME` / `MQTT_BRIDGE_PASSWORD` env vars; the bridge
  uses these to connect.
- [ ] A new `iot-api` background task (started from FastAPI `lifespan`,
  not a separate container) connects to the broker, lists devices
  whose `supportedProtocol == "mqtt"` and `mqttTopicRoot` is set, and
  subscribes to `<mqttTopicRoot>/+`.
- [ ] On each received message: parse JSON, route the **last topic
  segment** to a single Orion attribute on `Device:<deviceId>` via
  `POST /v2/entities/{id}/attrs` (the existing `OrionClient.patch_entity`
  path). Numeric payloads → `Number`, boolean → `Boolean`, string →
  `Text`, JSON object → `StructuredValue`.
- [ ] If `dataTypes` is set on the device, the value is **type-checked
  against the matching key** before being forwarded; mismatches are
  dropped with a `WARNING` log line and a counter increment, not a
  crash.
- [ ] When a device is created / patched / deleted via the existing
  `/devices` endpoints, the bridge updates its subscription list
  within `≤ 5 s` (no service restart). Tested by the integration suite.
- [ ] Malformed JSON, missing `dataTypes` entry, oversized payload
  (`> 64 KiB`), or unknown topic segment are dropped with a single
  log line each — never propagated as a 5xx and never blocking other
  messages.
- [ ] `GET /api/v1/system/mqtt` (admin-only) returns
  `{ connected: bool, subscribed_topics: int, last_message_at: iso8601
  | null, dropped_invalid: int }` for ops visibility. Replaces no
  existing endpoint.
- [ ] Integration test: the suite spins up Mosquitto + iot-api +
  Orion + QL + Crate via Compose (existing `make test` stack),
  registers a device, publishes a JSON message with `paho-mqtt`,
  and asserts (a) the value appears under `GET /devices/{id}/state`
  within 2 s and (b) a row exists in CrateDB within 5 s.
- [ ] RBAC: nothing user-facing changes. Ingestion does not require a
  Keycloak account — the bridge is a back-end worker authenticating
  to Mosquitto with its own credentials.
- [ ] `make test` stays 100% green; no regression in the existing
  145-test suite.

## Out of scope

- HTTP / CoAP ingestion endpoints (those are ticket **0019**).
- TLS on MQTT, mutual TLS, ACLs per device. The dev broker uses one
  shared username/password and listens on plaintext only.
- Per-device MQTT credentials. The bridge is the single subscriber;
  individual sensors connect with the shared `sensor` account
  provisioned for them in a later operability ticket.
- Decoding LoRaWAN payloads or running JS decoder functions
  (`payload_decoder` field): forwarded raw, decoded later.
- PLC / Modbus polling (ticket **0031** stretch).
- Charts in the UI (ticket **0020**).
- Floor-plan live overlay (ticket **0021**).
- Alerts and rule evaluation (ticket **0022**).
- Sending commands back to a device (ticket **0023**).
- Audit log of received messages (ticket **0024**).
- Backpressure / message queuing across iot-api restarts. The bridge
  is best-effort: on restart it resubscribes, but messages published
  during the outage are lost. Persistent buffering is a Phase 3
  problem.

## Open questions

1. **Topic shape**: spec says `mqttTopicRoot` is the *root*; this
  ticket assumes the convention `<mqttTopicRoot>/<attribute_name>`
  with a single trailing segment. Confirm this is what real sensors
  will publish, or choose a JSON-payload convention
  (`{"<attr>": <value>}` on `mqttTopicRoot` itself with no
  per-attribute subtopic).
2. **Numeric coercion**: should an integer payload `42` published on
  a topic whose `dataTypes` says `"float"` be accepted (cast to
  `42.0`) or rejected? Proposed: accept and cast.
3. **Wildcard depth**: `<mqttTopicRoot>/+` is one level. If a device
  publishes on `<mqttTopicRoot>/<area>/<attr>` (two levels deep),
  it will not match. Proposed: keep one level for v1; document the
  constraint and revisit in 0019/0023.
4. **Bridge placement**: in-process background task vs. separate
  `iot-mqtt-bridge` container. Proposed: in-process for simpler ops
  (one service to scale, one log stream, shared DB session) — at
  the cost of coupling broker availability to API uptime. Open to
  reverse if you'd rather isolate.
