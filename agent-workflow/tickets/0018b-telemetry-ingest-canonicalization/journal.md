# Journal — Ticket 0018b

## 2026-05-05 — Opened
Filed straight to `in-progress` after 0018a closed; user pre-approved
("all default"), so requirements + design landed together.

## 2026-05-05 — Implementation
- **`mqtt_bridge.py`**: imported `DuplicateEntity`; rewrote `_forward`
  to compute one `now` and write `{<attr>, dateLastValueReported}` to
  the `Device` entity in the same patch (one Orion round-trip instead
  of two). Added `_upsert_measurement(device_urn, attr, value, ts_iso)`:
  `create_entity` then on `DuplicateEntity` → `patch_entity` of just
  `numValue` + `dateObserved`. Both fall-back paths log at WARNING
  and swallow the error per the design.
- **Decision (deviation from design wording, not behaviour):** I pass
  the ISO string into `_upsert_measurement` rather than the raw
  `datetime`, because both call sites need the same string already.
  Saves one redundant `.isoformat()` call. Signature is private so
  no contract impact.
- **Decision:** measurement URN suffix uses
  `attr[:1].upper() + attr[1:]` to mirror exactly the rule already
  used by `app/routes/telemetry.py::_measurement_urn`. Consistency
  beats prettier capitalisation rules.
- **Decision:** `unitCode` is omitted on the upsert (resolved
  default). When 0020 needs unit-aware charts we'll either add a
  controlled-vocabulary mapping (mirroring the `UNITS` table in
  `add_test_data.py`) or surface the value via a separate
  device-level attribute. Either way, that's not telemetry-ingest's
  concern.
- **Tests:** three new integration cases in
  `tests/test_mqtt_bridge.py`. The "two publishes" test inserts a
  small `time.sleep(1.2)` between publishes so QuantumLeap has a
  distinct `time_index` for the second row; without it the second
  row collapses into the first.
- **Result:** 10/10 in `test_mqtt_bridge.py` green; 170/171 across
  the full suite. The single failure is the long-tracked
  `test_query_lastN_limits_results` flake (see
  `agent-workflow/memory/gotchas.md`), unrelated to this change.

## 2026-05-05 — Surprises / lessons
- None major. The Orion 422 "Already Exists" path was already coded
  in `OrionClient` (`DuplicateEntity`) so the fallback was a one-line
  branch.
- The `_wait_until` helper from 0018 was sufficient for the new
  tests; no extra timing primitives needed.
