# Journal — Ticket 0019

## 2026-05-05 — Opened
Filed straight to `in-progress` with requirements + design + tasks
together; user pre-approved with "all default".

## 2026-05-05 — Implementation
- **Canonical writer extracted** into `app/ingest.py`. Two helpers:
  `upsert_measurement(orion, urn, attr, value, ts_iso, unit_code?)`
  and `apply_measurement(orion, urn, attr, ngsi_type, value, ts_iso?,
  unit_code?)`. The bridge's old private `_upsert_measurement` is
  gone; `_forward` is now a six-line wrapper that does payload
  parsing/validation and delegates. The MQTT tests (10) all stayed
  green on first run, which is the strongest signal that the
  refactor was clean.
- **Auth model**: per-device API key, header `X-Device-Key`, SHA-256
  hash in Postgres. The cleartext is shaped `dik_<8hex>_<32hex>`.
  - **Decision (small deviation):** the design said "store the
    prefix in clear" with 8 chars; I store 12 (`dik_<8hex>` =
    12 chars including the 4-char tag) so that an admin UI can
    show a recognisable bucket without ambiguity. No security cost.
  - **Decision:** verification uses `hmac.compare_digest` against
    the stored hash. Constant-time comparison is the right reflex
    even if it's not strictly necessary against a SHA-256 of a
    256-bit secret.
- **Body shape**: a single `TelemetryIngestIn` schema accepts either
  the single-measurement top-level fields **or** `measurements: [...]`,
  validated by a `model_validator` that rejects both/neither. The
  full batch is validated up front; if any entry fails, no Orion
  call is made (AC: no partial writes).
- **`dataTypes` source**: rather than hitting Postgres, I read the
  device entity from Orion once at the top of the request and pull
  `dataTypes` via `from_ngsi`. One round-trip per request, regardless
  of batch size.
- **delete_device cleanup**: I added a one-line
  `DELETE FROM device_ingest_keys WHERE device_id = ?` to the
  existing `DELETE /devices/{id}` handler, mirroring the
  pre-existing `MaintenanceLog` cleanup. Out-of-scope strictly, but
  surgical and the alternative (orphaned key rows) would be a
  silent footgun.
- **Test fixture**: added an `anon` httpx.Client (no admin Bearer)
  so ingest tests can prove the call works with **only**
  `X-Device-Key`. The existing `api` fixture is admin-bearered and
  is used for key issue / revoke / device CRUD.
- **Result**: `make test` 182 passed (was 170 before 0018b → +3 in
  0018b → +12 in 0019), 1 pre-existing flake unrelated.

## 2026-05-05 — Surprises / lessons
- The `dataTypes` field on the API is gated to `mqtt` protocol in
  `_PROTOCOL_FIELDS`, so an `http`-protocol device has no
  `dataTypes`. For now I let HTTP-only devices skip validation
  (empty `data_types` dict → all values pass the existing
  `validate_against_dataTypes`). When 0020 surfaces a `dataTypes`
  editor we should consider lifting `dataTypes` out of the
  mqtt-only bag. Not a 0019 problem.
- The auth header decision (`X-Device-Key` vs reusing
  `Authorization: Bearer`) is consequential: oauth2-proxy strips
  unknown `Authorization` flavours from upstream requests. Custom
  header avoids the headache entirely.
