# Review — Ticket 0019

## What changed

New files:
- `platform/api/app/ingest.py` — canonical writer
  (`apply_measurement`, `upsert_measurement`).
- `platform/api/app/models_ingest_keys.py` — `DeviceIngestKey` ORM.
- `platform/api/app/schemas_ingest.py` — request/response models.
- `platform/api/app/routes/ingest.py` — three routes:
  `POST /devices/{id}/ingest-key`, `DELETE /devices/{id}/ingest-key`,
  `POST /devices/{id}/telemetry`.
- `platform/api/alembic/versions/0004_device_ingest_keys.py`.
- `platform/api/tests/test_http_ingest.py` — 12 integration tests.

Modified:
- `platform/api/app/mqtt_bridge.py` — `_forward` now delegates to
  `app.ingest.apply_measurement`; `_upsert_measurement` removed.
- `platform/api/app/main.py` — include `ingest.router`.
- `platform/api/app/routes/devices.py` — `delete_device` also
  drops the ingest key row (mirrors `MaintenanceLog` cleanup).
- `platform/api/alembic/env.py` — register new model.
- `platform/api/tests/conftest.py` — TRUNCATE adds
  `device_ingest_keys`.
- `agent-workflow/architecture.md` — Ingestion section rewritten
  (now covers MQTT + HTTP + auth); Routes section adds the two
  new endpoints.
- `agent-workflow/memory/gotchas.md` — dual-auth-ladder bullet.
- `agent-workflow/roadmap.md` — 0018b and 0019 flipped done.

## Acceptance criteria — evidence

- **A.1 issue/rotate** — `test_issue_then_rotate_changes_key`.
- **A.2 revoke** — `test_revoke_then_ingest_unauthorized`.
- **A.3 single ingest dual-write** —
  `test_ingest_single_lands_in_state_and_telemetry`.
- **A.4 explicit `ts`** —
  `test_ingest_with_explicit_ts_used_as_dateObserved`.
- **A.5 batch** — `test_ingest_batch_two_yields_two_entries`.
- **A.6 `dataTypes` mismatch** —
  `test_ingest_dataTypes_mismatch_422`.
- **A.7 401 paths** — `test_ingest_missing_key_401`,
  `test_ingest_wrong_device_key_401`,
  `test_ingest_key_endpoint_requires_role`.
- **A.8 unknown device** — `test_ingest_unknown_device_404`.
- **A.9 MQTT path unchanged** — all 10 mqtt-bridge tests stayed
  green on first run after the bridge refactor.
- **B `make test`** — 182 passed, 1 pre-existing flake
  (`test_query_lastN_limits_results`).
- **C single canonical writer** — `app.ingest.apply_measurement`
  is the only place that writes the dual artefact; both MQTT and
  HTTP call it.

## Follow-ups (not in scope)

- **FU1** UI: a "HTTP ingest key" panel on the device detail page
  (operator can issue / rotate / copy-once; admin can revoke).
  Goes naturally with 0020.
- **FU2** Per-device or per-key rate limiting + audit log on
  `device_ingest_keys.last_used_at` deltas. Phase 3.
- **FU3** Multi-key per device with overlapping rotation windows.
  Wait for a real customer ask.
- **FU4** Webhook signature verification (Chirpstack `Authorization`
  header → `X-Device-Key` shim) — Phase 3.
- **FU5** Lift `dataTypes` out of the mqtt-only protocol bag so
  HTTP-only devices can declare expected types and benefit from
  the same validation. Drives 0020's `dataTypes` editor.

## Self-review notes

- The endpoint returns `202 Accepted` because a successful response
  doesn't mean QuantumLeap has indexed the row yet — it means Orion
  accepted the writes. `200 OK` would imply synchronous availability
  in `/telemetry`, which is not true (≤ ~1 s lag).
- One Orion `GET /v2/entities/{urn}` is the only round-trip we
  spend on auth+validation regardless of batch size. Per-entry cost
  is `1 PATCH Device + (Number ? 1 POST/PATCH Measurement : 0)`.
- The `last_used_at` UPDATE happens after all writes succeed; if
  Orion fails partway through a batch, the bookkeeping isn't
  written. Acceptable: it's a nice-to-have, not auth-critical.
- The custom header (`X-Device-Key`) chosen over
  `Authorization: Bearer` is deliberate — oauth2-proxy can interfere
  with `Authorization`. Documented in the gotchas memory.

## External review
(none yet)
