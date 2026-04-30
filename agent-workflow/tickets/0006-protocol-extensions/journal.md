# Journal

## Decisions

- Single shared helper `validate_protocol_invariants(merged, protocol)` is the
  source of truth for "required fields per protocol" + "no foreign-protocol
  fields". `DeviceIn` runs it on POST; the PATCH route runs it on the
  Orion-merged dict. Same rule, two call sites, no duplication.
- PATCH validates against the merged state by `from_ngsi(existing) | patch`.
  This is correct because `from_ngsi` already returns a flat API-shaped dict.
- Field-format validators live on `_DeviceCommon` (`field_validator`), so they
  run automatically on both `DeviceIn` and `DeviceUpdate`. No re-validation on
  the merge step needed for format — Pydantic already did it on the PATCH
  parse.
- IPv4-only for `plcIpAddress`. Spec example is IPv4 and PLC networks are
  effectively never IPv6 in the field. Trivial to extend later.
- MQTT topic regex deliberately rejects subscription wildcards (`+`, `#`)
  even though they are technically valid topic characters elsewhere — they
  are subscription syntax and never appear in publish topics. Whitespace is
  rejected because Orion stores topics as plain strings and trimming
  surprises are worse than a 422.

## Lessons

- Pydantic v2 `field_validator` with multiple field names (`@field_validator(
  "loraAppEui", "loraDevEui")`) is the cleanest way to share format rules.
- Cross-validation that depends on stored state (PATCH against existing
  entity) belongs in the route, not the schema. Schemas validate single
  payloads; routes validate state transitions.
- `Protocol(value)` raises `ValueError` for unknown enum values; we trap it
  and re-raise as 422 to keep the error contract.

## Flake observed

`tests/test_telemetry.py::test_query_lastN_limits_results` failed once in
this ticket's first full-suite run (got `[52, 54]` instead of `[53, 54]`).
QL ingestion is async and a single missed measurement explains it. Passed
on retry and on the next full-suite run. Not in scope to fix here; flagged
as a follow-up for the test-stability ticket.
