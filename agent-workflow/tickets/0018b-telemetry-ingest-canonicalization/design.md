# Design — Ticket 0018b

## Approach

Extend `MqttBridge._forward()` so each successful publish performs
**two** Orion writes instead of one:

1. **Device patch (existing):** `POST /v2/entities/<deviceUrn>/attrs`
   with `{<attr>: {type, value}, dateLastValueReported: {type:DateTime,
   value: <now>}}`. The added `dateLastValueReported` is what 0020's
   freshness badge will read.
2. **DeviceMeasurement upsert (new), only when `ngsi_type == "Number"`:**
   - Compute `measurement_urn = urn:ngsi-ld:DeviceMeasurement:<uuid>:<Attr>`
     using the same suffix rule as
     `app/routes/telemetry.py::_measurement_urn` (first letter
     uppercased).
   - Build the entity body:
     ```python
     {
       "id": measurement_urn,
       "type": "DeviceMeasurement",
       "refDevice": {"type": "Text", "value": device_urn},
       "controlledProperty": {"type": "Text", "value": attr},
       "numValue": {"type": "Number", "value": value},
       "dateObserved": {"type": "DateTime", "value": now_iso},
     }
     ```
   - Call `OrionClient.create_entity(body)`. On `DuplicateEntity`,
     fall back to `OrionClient.patch_entity(measurement_urn,
     {"numValue": ..., "dateObserved": ...})`. This mirrors the
     pattern already proven in `platform/scripts/add_test_data.py`.
   - On `OrionError`, log at WARNING and continue — the Device patch
     stays committed; we do not retry, do not raise, do not block.

The single-helper requirement (AC C bullet 1) is satisfied by adding a
private `_upsert_measurement(device_urn, attr, value, ts)` method on
`MqttBridge`. Extracting to a module is unnecessary at ~25 lines; if
0019 also lives inside `iot-api`, it can reuse the method by calling
the bridge instance via `request.app.state.mqtt_bridge`.

The `dateLastValueReported` write is unconditional (any successful
publish, including Boolean / Text) so the freshness badge in 0020
stays meaningful even when the value is not a `Number`.

## Alternatives considered

- **A) Subscribe Orion → QL on `Device.<attr>` and let QL persist
  Device-typed rows.** This is what 0018 effectively did. Rejected:
  the `/telemetry` endpoint and the data model are explicit that
  history lives under `DeviceMeasurement`. Reshaping `/telemetry` to
  read `Device` rows would re-introduce the inconsistency `0002`
  pinned away.
- **B) Have the bridge publish a synthetic NGSI message into Orion
  via a separate "ingestion" endpoint.** Rejected: extra hop, no
  benefit; Orion's `POST /v2/entities` is the synthetic endpoint.
- **C) Move the upsert into a background queue/worker.** Rejected
  for v1: `_forward` is already async and runs on the asyncio loop;
  one more `httpx` call adds ~5 ms. Backpressure is bounded by the
  existing `_INFLIGHT_CAP = 256`.
- **D) Resolve `unitCode` from a hard-coded map.** Rejected: out of
  scope per `requirements.md`; leaving `unitCode` absent is valid
  per the data model (`unitCode` is optional).

## Affected files / new files

- `platform/api/app/mqtt_bridge.py` — extend `_forward`; add private
  `_upsert_measurement`; add `from app.orion import DuplicateEntity`.
- `platform/api/tests/test_mqtt_bridge.py` — three new tests
  (`test_publish_lands_in_state_and_telemetry`,
  `test_two_publishes_yield_two_entries`,
  `test_boolean_publish_creates_no_measurement`).
- `agent-workflow/architecture.md` — rewrite the "Ingestion
  (current)" subsection to drop the "0018b is pending" caveat and
  describe the dual write.
- `agent-workflow/tickets/0018-mqtt-broker-and-bridge/tasks.md` —
  tick the previously-deferred "publish appears in `/telemetry`"
  smoke check, with a `(closed by 0018b)` annotation.
- Ticket folder paper trail (status, journal, review, tasks).

No compose change, no new dependency, no Alembic, no schema, no
front-end change.

## Data model / API contract changes

None. The `DeviceMeasurement` shape is pinned in
`agent-workflow/data-model.md` and already produced by
`add_test_data.py`. The `dateLastValueReported` attribute on `Device`
is already part of the schema (`_STATE_ATTRS` in `routes/telemetry.py`
includes it).

## Risks

- **Risk:** an Orion outage during the measurement upsert leaves
  `/state` updated but `/telemetry` empty for that publish.
  **Mitigation:** WARNING-log the gap; counter the symptom in
  monitoring later (0026 health page). Acceptable for v1.
- **Risk:** the DateTime format Orion accepts is stricter than
  Python's `datetime.isoformat()`.
  **Mitigation:** match `add_test_data.py` exactly
  (`isoformat().replace("+00:00", "Z")`).
- **Risk:** the test asserts a value within 4 s; QL ingestion lag
  could push that. **Mitigation:** poll up to 6 s with the same
  `_wait_until` helper already in `test_mqtt_bridge.py`; raise the
  budget if CI flakes.

## Test strategy for this ticket

- Unit: none (the change is one `httpx` round-trip; covered by
  integration).
- Integration: three new cases against the live stack (see Affected
  files). Each test cleans up the device entity via the existing
  `created_ids` fixture, which already deletes both `Device` and
  `DeviceMeasurement` entities from Orion.
- Manual verification:
  ```bash
  make up && make seed   # for token + a known-MQTT device
  # pick an MQTT device id from `make seed` output, set DEV_UUID
  mosquitto_pub -h localhost -p 1883 -u bridge -P change-me-bridge \
    -t "<mqttTopicRoot>/temperature" -m '{"value": 24.7}'
  curl -H "Authorization: Bearer $TOKEN" \
    "http://localhost/api/v1/devices/urn:ngsi-ld:Device:$DEV_UUID/state"
  # → attributes.temperature.value == 24.7, dateLastValueReported set
  curl -H "Authorization: Bearer $TOKEN" \
    "http://localhost/api/v1/devices/urn:ngsi-ld:Device:$DEV_UUID/telemetry?controlledProperty=temperature"
  # → entries has at least one row with numValue == 24.7
  ```
