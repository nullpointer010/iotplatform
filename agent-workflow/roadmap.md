# Roadmap

Tickets are processed in order unless re-prioritized. Only one ticket is
`in-progress` at any time. Stubs below are intentionally short until promoted
to active.

## Phase 1 — Foundation

Source of truth for endpoints + data model is `context/doc/backend.md`.
Each code ticket ships its own pytest suite (good/bad/missing/unknown
inputs) in the same PR as the routes it adds. `make test` runs the suite
against the live `make up` stack.

- [x] **0001 platform-skeleton-audit** — *(done 2026-04-30)*
  Canonical `platform/` layout, top-level `Makefile`, full Compose stack
  with bumped images (crate 6.2.6, postgres 17.9, mongo 8.2.7, orion 4.4.0,
  quantumleap 1.0.0). Frozen `context/platform/` as historical reference.

- [x] **0002 data-model-decision** — *(done 2026-04-30)*
  Doc-only. Pinned strategy (c): flat schema, FIWARE Smart Data Models
  naming, no full SDM adoption. Pinned `Device` base attributes,
  per-protocol extensions (MQTT/PLC/LoRaWAN), `DeviceMeasurement`
  telemetry convention, CrateDB monthly partitioning, API-via-QuantumLeap
  query path, HTTP error contract. Output: `agent-workflow/data-model.md`.

- [x] **0003 devices-crud-orion** — *(DONE)*
  `POST/GET/GET-by-id/PATCH /api/v1/devices` proxied to Orion Context
  Broker following the pinned data model from 0002. Pytest suite covering
  valid create (201), missing required fields (422), wrong types (422),
  unknown id (404), duplicate id (409), partial update (200), update of
  unknown id (404), list empty / list populated. `make test` target wired.

- [x] **0004 telemetry-and-state** — *(DONE)*
  `GET /api/v1/devices/{id}/telemetry` (date range + pagination, via
  QuantumLeap) and `GET /api/v1/devices/{id}/state` (current attribute
  values via Orion). Verify Orion → QL → CrateDB ingestion end to end with
  a simulated sensor. Tests: ingest sample, query empty range, query with
  data, malformed date range (400), unknown device (404).

- [x] **0005 maintenance-log** — *(DONE)*
  Postgres `maintenance_operation_types` + `maintenance_log` schema from
  `context/doc/backend.md` via Alembic. Endpoints per spec
  (`POST/GET /devices/{id}/maintenance/log`,
  `PATCH/DELETE /maintenance/log/{id}`,
  `GET/POST/PATCH/DELETE /maintenance/operation-types`). Tests:
  create/list/patch/delete log, FK to nonexistent device (404), bad
  operation_type (422).

- [x] **0006 protocol-extensions** — *(DONE)*
  Per-type metadata validation: MQTT, PLC, LoRaWAN. Cross-protocol field
  rejection, field-format validation (MQTT topic, IPv4, hex EUIs/AppKey),
  PATCH cross-validates against merged Orion state.

- [x] **0007 web-ui-skeleton** — *(DONE)*
  Next.js 14 App Router + TypeScript + Tailwind + Radix UI + react-hook-form +
  Zod + TanStack Query under `web/`. Crop palette mapped to HSL tokens.
  Pages: dashboard, devices list/new/detail (overview + telemetry +
  maintenance tabs)/edit, operation types catalog. Delete dialogs across
  all entities. User menu placeholder (real auth deferred to 0009).
  Backend additions: CORS middleware (`cors_allow_origins` setting) and
  `DELETE /devices/{id}` (cascades maintenance log).

- [x] **0008 ui-iteration-1** — *(DONE)*
  First UI iteration on top of the 0007 skeleton: complete the device
  form (Location with `site_area`, Administrative section, JSON fields
  for `address` / `mqttSecurity` / `plcCredentials` / `plcTagsMapping` /
  `controlledProperty`), client-side search/filter/sort + clear on the
  devices list, and a `Site area` column. Backend extends `GeoPoint` with
  optional `site_area` and switches `location` to `StructuredValue` (with
  back-compat parsing of legacy `"lat,lon"` strings). Adds
  `platform/scripts/add_test_data.py` (≈50 devices, 8 op-types, 150
  maintenance entries, telemetry pushed via Orion → QL) and a `make seed`
  target.

- [ ] **0009 pdf-manual-upload** — *(optional, post-spec)*
  Out of `backend.md` scope. Implement only if still wanted after 0003–0008
  land.

- [ ] **0010 keycloak-integration** — *(TODO, last)*
  Keycloak service + JWT middleware + RBAC retrofitted onto every endpoint
  from 0003–0008. Tests for unauthenticated (401), wrong-role (403),
  authorized (200) on each route.

## Phase 2+ — Later

Phase 2 (MQTT/CoAP/HTTP ingestion, realtime), Phase 3 (Superset, H2O,
Node-RED, NiFi, Airflow, MinIO at scale, Prometheus/Grafana) and
Kubernetes deployment are out of scope until Phase 1 closes.
