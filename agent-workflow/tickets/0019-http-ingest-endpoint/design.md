# Design — Ticket 0019

## Approach

Three pieces, all small:

### 1. Canonical writer (`app/ingest.py`)

Pure async helpers, no FastAPI imports. Currently `MqttBridge` owns
`_upsert_measurement`; we extract it so the HTTP route and the
bridge call the same code.

```python
# app/ingest.py
async def upsert_measurement(orion, device_urn, attr, value, ts_iso): ...
async def apply_measurement(orion, device_urn, attr, ngsi_type, value, ts):
    """Dual write: patch Device (with dateLastValueReported), upsert
    DeviceMeasurement when ngsi_type == 'Number'."""
```

`MqttBridge._forward` becomes a thin wrapper over `apply_measurement`.
The bridge keeps payload validation and stats; the dual-write moves out.

### 2. Ingest auth (`device_ingest_keys` table)

One row per device, written via two new routes on the existing
`devices` router family but housed in a new `routes/ingest.py`:

- `POST   /devices/{id}/ingest-key` (operator) → upsert; returns the
  cleartext key once.
- `DELETE /devices/{id}/ingest-key` (admin) → delete.

Schema:
```sql
CREATE TABLE device_ingest_keys (
  device_id    UUID PRIMARY KEY,
  key_hash     VARCHAR(64) NOT NULL,    -- hex SHA-256
  prefix       VARCHAR(12) NOT NULL,    -- first chars, for UX listing
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by   VARCHAR(255),
  last_used_at TIMESTAMPTZ
);
```

Key shape: `dik_<8-hex-prefix>_<32-hex-secret>` (40 chars total).
SHA-256 is enough — the secret is high-entropy random, no need for
bcrypt; a per-request bcrypt would dominate latency. The prefix is
stored in plaintext so an admin UI can show "dik_abcd1234_…" without
revealing the secret.

Verification (per request):
1. Header `X-Device-Key` present? else 401.
2. Hash incoming key with SHA-256.
3. Look up row by `device_id` (URN → UUID extraction).
4. `hmac.compare_digest(stored_hash, computed_hash)` → 401 on miss.
5. Async-update `last_used_at = now()` (fire-and-forget; not awaited
   to keep the hot path tight is fine, but for v1 we just await it
   inside the request — it's one cheap UPDATE).

### 3. Ingest endpoint

`POST /api/v1/devices/{id}/telemetry` with `X-Device-Key`. Body is
either:

```json
{"controlledProperty": "temperature", "value": 24.7, "ts": "...?", "unitCode": "..?"}
```
or:
```json
{"measurements": [ ... ]}
```

Pydantic enforces "exactly one of `controlledProperty` / `measurements`".
Per-entry validation:

1. `controlledProperty` matches `^[A-Za-z0-9_]+$` (same as
   `routes/telemetry.py` query param).
2. `value` infers an NGSI type via the existing
   `app.mqtt_payload.infer_ngsi_type` (we reuse it instead of
   duplicating the bool-vs-int logic).
3. `validate_against_dataTypes` (also from `mqtt_payload`) passes.
4. `ts` parses as ISO-8601 with timezone; default = `now(UTC)`.

If **all** entries pass validation, we await
`apply_measurement(...)` for each in order, then return
`{"accepted": N}`. Any single validation failure short-circuits
with `422` and no Orion call.

Note: we do not GET the `Device` entity from Orion just to read
`dataTypes`. Instead, the route fetches the device once at the top
of the request (one Orion `GET /v2/entities/{urn}`), uses
`from_ngsi(...)` to extract `dataTypes`, then validates, then
writes. One round-trip per ingest request, regardless of batch size.

## Alternatives considered

- **A) Service-account JWT instead of API key.** Simpler from the
  realm side ("just another client") but every gateway / TTN setup
  has to learn how to refresh JWTs. API keys are the IoT-industry
  default for a reason. Rejected.
- **B) Multiple keys per device (rotation overlap).** Useful if you
  can't update sensors atomically. v1 single-key is fine; the
  rotation story is "issue → reconfigure → next request flips over".
  Multi-key can land in a follow-up if a real customer hits the case.
- **C) Bcrypt the key.** Bcrypt at the cost-factor we'd choose
  (~250 ms) makes the endpoint unusable under load. The secret has
  256 bits of entropy; SHA-256 is the right tool.
- **D) PUT /telemetry to mirror REST conventions.** POST is correct
  here: each call appends a new measurement (non-idempotent in QL's
  history). Rejected.
- **E) Reuse the Keycloak JWT path with a synthetic role.** Pollutes
  the role catalog and forces every sensor through Keycloak.
  Rejected.

## Affected files

New:
- `platform/api/app/ingest.py`
- `platform/api/app/models_ingest_keys.py`
- `platform/api/app/schemas_ingest.py`
- `platform/api/app/routes/ingest.py`
- `platform/api/alembic/versions/0004_device_ingest_keys.py`
- `platform/api/tests/test_http_ingest.py`
- `agent-workflow/tickets/0019-http-ingest-endpoint/{status,requirements,design,tasks,journal,review}.md`

Modified:
- `platform/api/app/mqtt_bridge.py` — `_forward` delegates to
  `app.ingest.apply_measurement`; `_upsert_measurement` removed.
- `platform/api/app/main.py` — include `ingest.router`.
- `platform/api/alembic/env.py` — `from app import models_ingest_keys`.
- `platform/api/tests/conftest.py` — add `device_ingest_keys` to the
  `pg_clean` TRUNCATE.
- `agent-workflow/architecture.md` — extend the "Ingestion (current)"
  subsection with the HTTP path; add a tiny "Ingest auth" note.
- `agent-workflow/data-model.md` — note the new auth artefact.
- `agent-workflow/memory/gotchas.md` — one bullet on the dual-auth
  story (Keycloak for users, X-Device-Key for sensors).
- `agent-workflow/tickets/0019-http-ingest-endpoint/status.md` →
  `done` at close.

## Risks

- **Replay**: an exposed key allows replay until rotated. v1
  acceptance: HTTPS in prod (0028) is the mitigation; we don't add
  per-message HMAC.
- **Header collision** with oauth2-proxy: using a custom header
  (`X-Device-Key`) avoids stomping on Keycloak's `Authorization`.
- **Tests + Keycloak**: the `api` fixture already injects a Keycloak
  bearer for admin. Ingest tests bypass it for the actual ingest
  call (use a raw `httpx.Client` without the admin bearer, just the
  `X-Device-Key`). Key-management calls use the admin client.

## Test strategy

`tests/test_http_ingest.py`:
- `test_issue_then_rotate_changes_key`
- `test_revoke_then_ingest_unauthorized`
- `test_ingest_single_lands_in_state_and_telemetry`
- `test_ingest_batch_two_yields_two_entries`
- `test_ingest_with_explicit_ts_used_as_dateObserved`
- `test_ingest_dataTypes_mismatch_422`
- `test_ingest_missing_key_401`
- `test_ingest_wrong_device_key_401`
- `test_ingest_unknown_device_404`
- `test_ingest_no_unit_code_when_omitted`

Manual smoke (after `make up`):
```bash
ID=urn:ngsi-ld:Device:<uuid>; TOKEN=...
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/v1/devices/$ID/ingest-key
# → {"key":"dik_xxxx_yyyy","prefix":"dik_xxxx","createdAt":"..."}
KEY=dik_...
curl -X POST -H "X-Device-Key: $KEY" -H "Content-Type: application/json" \
  http://localhost/api/v1/devices/$ID/telemetry \
  -d '{"controlledProperty": "temperature", "value": 24.7}'
# → {"accepted":1}
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/devices/$ID/telemetry?controlledProperty=temperature"
# → {"entries":[{"numValue":24.7,...}]}
```
