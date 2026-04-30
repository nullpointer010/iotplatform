# 0006 — Design

## Surface
Touches:
- `platform/api/app/schemas.py` — validators + new helper.
- `platform/api/app/routes/devices.py` — PATCH calls the merged-state validator.
- `platform/api/tests/test_protocol_extensions.py` — new behaviour tests.

No DB / compose / Alembic / dependency changes.

## schemas.py

### Cross-protocol field map
```
_PROTOCOL_FIELDS: dict[Protocol, tuple[str, ...]] = {
    Protocol.mqtt: ("mqttTopicRoot", "mqttClientId", "mqttQos", "dataTypes",
                    "mqttSecurity"),
    Protocol.plc:  ("plcIpAddress", "plcPort", "plcConnectionMethod",
                    "plcCredentials", "plcReadFrequency", "plcTagsMapping"),
    Protocol.lorawan: ("loraAppEui", "loraDevEui", "loraAppKey",
                       "loraNetworkServer", "loraPayloadDecoder"),
}
```
`_PROTOCOL_REQUIRED` stays as-is (subset of the above).

### Field-format validators on `_DeviceCommon`
- `mqttTopicRoot`: regex `^[^/+#\s][^+#\s]*[^/+#\s]$|^[^/+#\s]$`. Practical
  rule: no leading/trailing `/`, no whitespace, no `+`/`#` wildcards.
- `plcIpAddress`: `ipaddress.IPv4Address(value)`.
- `loraAppEui`, `loraDevEui`: `^[0-9A-Fa-f]{16}$`.
- `loraAppKey`: `^[0-9A-Fa-f]{32}$`.

### Shared invariant helper
```
def validate_protocol_invariants(merged: dict, protocol: Protocol) -> None:
    """Raise ValueError if `merged` violates protocol required-fields or
    cross-protocol-leak rules."""
```
- Reuses `_PROTOCOL_REQUIRED` and `_PROTOCOL_FIELDS`.
- Used by `DeviceIn._check_protocol_requirements` (POST) and by the PATCH
  route after merging.

## routes/devices.py — PATCH flow
1. `_normalise_id_or_400`.
2. Fetch existing entity → `from_ngsi(entity)` → `current` dict.
3. `merged = {**current, **patch.model_dump(exclude_none=True)}`.
4. Determine effective protocol = `merged.get("supportedProtocol")`.
5. Coerce string→`Protocol` enum.
6. `validate_protocol_invariants(merged, protocol)` — on `ValueError` raise
   `HTTPException(422)`.
7. Existing `orion.patch_entity` call.

The format validators on `_DeviceCommon` run automatically on both POST and
PATCH because `DeviceUpdate` extends it.

## Tests (`tests/test_protocol_extensions.py`)
~14 cases covering AC1–AC7. Use existing `created_ids` fixture for cleanup.

## Risks
- PATCH validation is a new rejection path. Expected: spec compliance.
- IPv4-only `plcIpAddress`: deliberately documented in journal.
