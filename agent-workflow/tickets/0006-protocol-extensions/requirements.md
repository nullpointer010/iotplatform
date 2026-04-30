# 0006 — Protocol extensions: tighter validation

## Why
Ticket 0003 enforced "required fields per protocol" only on `POST /devices`.
Real gaps remain:

1. **PATCH bypass.** `DeviceUpdate` accepts a partial payload that, when merged
   with the stored entity, leaves the device in an invalid state for its
   `supportedProtocol` (e.g. `PATCH` switching to `mqtt` without
   `mqttTopicRoot`).
2. **Cross-protocol leak.** Nothing prevents a `http` device from being created
   with `mqttTopicRoot` set, or an `mqtt` device from carrying `plcIpAddress`.
3. **No field-format validation.** MQTT topic, PLC IP, LoRaWAN EUIs/AppKey are
   stored as free text. Spec implies clear shapes.

## Acceptance criteria

POST /devices:
- AC1: cross-protocol fields rejected (e.g. `supportedProtocol=http` +
  `mqttTopicRoot` → 422).
- AC2: required-fields-per-protocol still enforced (regression of 0003).
- AC3: field-format validation:
  - `mqttTopicRoot` non-empty, no leading/trailing `/`, no MQTT wildcards
    (`+`, `#`).
  - `plcIpAddress` is a valid IPv4 address.
  - `loraAppEui`/`loraDevEui` are 16 hex chars.
  - `loraAppKey` is 32 hex chars.

PATCH /devices/{id}:
- AC4: PATCH that changes `supportedProtocol` must satisfy the new protocol's
  required fields against the merged state, else 422.
- AC5: PATCH that introduces a foreign-protocol field (relative to the
  merged `supportedProtocol`) → 422.
- AC6: PATCH with bad-format value (per AC3 list) → 422.
- AC7: PATCH no-op or in-protocol field updates keep working (200).

General:
- AC8: 55 existing tests stay green.

## Out of scope
- New protocols (CoAP/HTTP/Modbus/BACnet have no required extensions in spec).
- Secrets handling for `plcCredentials` / `loraAppKey` — deferred to 0009.
- Telemetry-side schema (already in 0004).
- IPv6 for `plcIpAddress` — IPv4 only for now.
