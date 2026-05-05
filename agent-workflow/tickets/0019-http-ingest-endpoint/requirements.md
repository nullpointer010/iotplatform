# Ticket 0019 — http-ingest-endpoint

## Problem

Today the only way to push real telemetry into the platform is MQTT
(0018 + 0018b). Real Almería deployments mix protocols: most of the
HVAC + greenhouse-controller fleet only speaks plain HTTP, and the
LoRaWAN sensors need a Chirpstack/TTN webhook. We need a small,
auth-protected HTTP ingestion endpoint that lands measurements in
the same canonical place 0018b just fixed (`DeviceMeasurement` + the
`Device` `dateLastValueReported`), so 0020 (charts), 0021 (floor-plan
overlay) and 0022 (alerts) work for non-MQTT devices too.

A sensor or webhook is **not** a Keycloak user — issuing them users +
JWTs is operational overhead and a security mistake. So the auth has
to be off the user-RBAC ladder: a per-device static API key that
operators can issue, rotate and revoke from the device record.

## Goal

`POST /api/v1/devices/{id}/telemetry` accepts one or many
measurements for that device, validates them against the device's
`dataTypes`, persists them via the same canonical writer that the
MQTT bridge uses, and authenticates with a per-device API key
issued/rotated/revoked through the existing device routes.

## User stories

- As a sensor operator, my HTTP-only sensor or my Chirpstack webhook
  posts JSON to `…/devices/{id}/telemetry` and the value shows up in
  `/state` and `/telemetry` exactly the same as for MQTT.
- As an integrator, I issue a per-device API key once
  (`POST .../ingest-key` returns the cleartext key one time),
  configure my device with it, and never need a Keycloak account.
- As an admin, I can rotate the key (re-POST returns a new one) or
  revoke it (DELETE) without touching Keycloak or the user catalog.

## Acceptance criteria

### A. Behaviour

- [ ] **Issue/rotate key** — `POST /api/v1/devices/{id}/ingest-key`
      returns `{"key": "<cleartext>", "prefix": "...", "createdAt":
      "..."}`. The cleartext is **only** returned by this call; the
      DB stores a SHA-256 hash. Calling it again rotates (replaces
      the row). Requires role `operator` (or `admin`).
- [ ] **Revoke key** — `DELETE /api/v1/devices/{id}/ingest-key`
      removes the row; subsequent ingest with the old key returns
      401. Requires role `admin`.
- [ ] **Single ingest** — `POST /api/v1/devices/{id}/telemetry`
      with header `X-Device-Key: <cleartext>` and body
      `{"controlledProperty": "temperature", "value": 24.7}`:
        1. patches the `Device` (same dual write as the MQTT bridge);
        2. when the value is numeric, upserts the
           `DeviceMeasurement:<uuid>:<Attr>` entity;
        3. responds `202 Accepted` with `{"accepted": 1}`.
- [ ] **Optional `ts`** — when the body includes
      `"ts": "2026-05-05T12:00:00Z"`, that ISO-8601 UTC timestamp is
      used as `dateObserved` instead of server clock.
- [ ] **Batch ingest** — body
      `{"measurements": [{...}, {...}]}` (2 ≤ N ≤ 100) processes
      every entry in declared order, returns
      `{"accepted": N}`. If any single entry fails validation, the
      whole batch is rejected with `422` (no partial writes).
- [ ] **`dataTypes` validation** — if the device's `dataTypes` map
      declares `temperature: Number` and the body sends a string,
      respond `422` with a clear detail (no Orion call).
- [ ] **Auth** — missing `X-Device-Key` → `401`. Wrong key (any
      string mismatch) → `401`. Key for a different device → `401`
      (constant-time check, but exact match is enough for v1).
- [ ] **Device 404** — POST to an unknown device URN responds
      `404`, regardless of the key state. (Fail fast on the URN
      shape; otherwise a typo would leak which devices exist.)
- [ ] **MQTT path unchanged** — refactoring `MqttBridge` to delegate
      to the new shared writer must not change the existing
      `tests/test_mqtt_bridge.py` outcomes.

### B. Tests

- [ ] New `platform/api/tests/test_http_ingest.py` covers: key
      issue + rotate + revoke, single ingest landing in
      `/state` and `/telemetry`, batch of two, optional `ts`,
      `dataTypes` mismatch → 422, missing/bad/foreign key → 401,
      unknown device → 404.
- [ ] Existing `tests/test_mqtt_bridge.py` (10 tests) still green.
- [ ] `make test` exits 0.

### C. Code shape

- [ ] A single canonical writer exists at
      `app.ingest.apply_measurement(orion, device_urn, attr,
      ngsi_type, value, ts)`. Both the HTTP route and
      `MqttBridge._forward` call it; no duplicated upsert logic.
- [ ] Ingest auth lives next to the route in
      `app.routes.ingest`, not in `app.auth` (the latter is for
      Keycloak / user RBAC).
- [ ] Alembic migration `0004_device_ingest_keys.py` creates the
      `device_ingest_keys` table (PK `device_id`, no FK — `Device`
      lives in Orion). One row per device.
- [ ] Architecture doc and `agent-workflow/data-model.md` reflect
      the new endpoint and the auth model.

## Out of scope

- Per-device rate limiting. The platform doesn't have any rate limit
  yet; adding one for one route is asymmetric. (Phase 3 ticket.)
- Multi-key support, key scopes, or expiry. v1 is one key per
  device, no expiry, rotated by re-issuing.
- Keycloak service-account JWTs. The roadmap allows them as an
  alternative; we pick API key (the simpler, more idiomatic option
  for IoT) and skip the JWT path entirely.
- Webhook signature verification (Chirpstack `Authorization:` headers
  etc.). The downstream operator is expected to map their gateway's
  auth to our `X-Device-Key`.
- Backfilling historical data. The endpoint is for live ingestion
  only; we accept a recent `ts` but don't sanity-check ranges.
- A separate batch endpoint for many devices in one request. Out of
  scope; per-device batch is enough.
- UI for the ingest key. 0020/0021 will surface it (a "Get HTTP
  ingest key" button on the device detail page) — not in 0019.

## Resolved decisions ("all default" 2026-05-05)

- Auth: per-device static API key (header `X-Device-Key`), one key
  per device, hashed with SHA-256, prefix stored in clear for UX.
- Body shape: single = `{controlledProperty, value, ts?}`,
  batch = `{measurements: [...]}` (mutually exclusive). Returns
  `202 Accepted, {"accepted": N}`.
- Ingest is fail-all on the batch: validation runs before any
  Orion call, so partial writes are impossible.
- `unitCode` accepted optionally; same shape as the data model.
- Role required: issuing a key = `operator`; revoking = `admin`.
- `_upsert_measurement` is extracted from `MqttBridge` to
  `app.ingest`. The bridge now delegates so 0019 and the bridge
  share one writer.
