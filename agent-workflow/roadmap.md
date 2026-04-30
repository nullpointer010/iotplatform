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

### Re-plan (2026-04-30)

After 0008 closed we re-planned the rest of Phase 1. Order is **visuals
first, then auth, then optional extras** so the platform stays easy to
demo while non-spec polish lands; spec closure (Keycloak per `backend.md`)
happens before the optional tickets.

Auth approach mirrors the CropDataSpace reference at
`/home/maru/crop-edc/cropdataspace`: Keycloak + oauth2-proxy at the edge
(no in-app login UI). Local dev only — no TLS, no Caddy hosts file
gymnastics; oauth2-proxy and Keycloak both bound to `localhost`.
i18n via `next-intl` (`es` default, `en` available).

- [x] **0009 almeria-seed-context** — *(done 2026-04-30)*
  Replaced the generic Spanish `SITES` list in
  `platform/scripts/add_test_data.py` with 8 IFAPA La Cañada + UAL
  Almería sites and IFAPA/UAL-tagged owners. Added a `_slug()` helper
  for `mqttTopicRoot` so multi-word cities (`"La Cañada"`) become valid
  MQTT segments (`la-canada`). Live `make seed`: 50/50 devices, 8
  op-types, 150 maintenance entries, 1872 telemetry points.

- [x] **0010 api-observability-fix** — *(done 2026-04-30)*
  Stopped Alembic's `fileConfig` from disabling uvicorn loggers
  (`disable_existing_loggers=False`). Added `RequestIdMiddleware` and a
  global `Exception` handler that logs via `app.errors` and returns
  `{detail, request_id}` with a matching `X-Request-ID` header.
  `PYTHONUNBUFFERED=1` set on the API container. 4 in-process pytest
  cases; 80/80 total green.

- [x] **0011 ux-polish-i18n** — *(done 2026-04-30)*
  Visual + interaction polish on top of the 0007/0008 skeleton: tighten
  the layout (less wall-of-text, better hierarchy, more whitespace,
  fewer columns by default with progressive disclosure), uniform toasts
  on every mutation, optimistic delete on list views, reusable
  empty-state CTA component, and `next-intl` integration with `es`
  (default) and `en` message catalogs. No new pages, no bulk delete,
  no new component library.

- [x] **0012 devices-external-map** — *(done 2026-04-30)*
  Leaflet + OSM tiles. Map view on devices list and on device detail
  using existing `location.latitude/longitude`. Click-to-pick coordinates
  in the device form. No API key, no paid tiles.

- [x] **0013 keycloak-and-edge-auth** — *(done 2026-04-30)*
  Keycloak 24 service + dedicated `keycloak-db` (postgres 17), realm
  `iot-platform` imported from `platform/config/keycloak/realm-iot.json`
  with 4 realm roles (`viewer`, `operator`, `maintenance_manager`,
  `admin`) and seed users for each. `oauth2-proxy` (keycloak-oidc) in
  front of the Next.js app, public client `iot-web`. Local dev,
  `localhost`-bound, no TLS. UI itself unchanged.

- [x] **0013b single-origin-edge** — *(done 2026-04-30)*
  oauth2-proxy becomes the only host-facing port (`:80`) and proxies
  both `/api/*` to the FastAPI container and `/*` to the Next.js dev
  server. `iot-api` no longer publishes a host port; same-origin
  fetches replace cross-origin CORS plumbing. Single `WEB_PORT`
  override; rolls in the `OAUTH2_PROXY_OIDC_AUDIENCE_CLAIMS=azp`
  hot-fix discovered during 0013 smoke-testing.

- [x] **0014 backend-jwt-rbac** — *(done 2026-04-30)*
  FastAPI validates JWTs against Keycloak's JWKS, exposes a
  `require_roles(*roles)` dependency, applies RBAC per `backend.md` to
  every route shipped in 0003–0008. Tests for 401 / 403 / 200 on a
  representative endpoint per resource. Closes the v1 spec.

- [x] **0015 web-role-aware-ui** — *(done 2026-04-30)*
  Web reads user identity + roles via a `/api/v1/me` echo. Hides
  actions the user cannot perform (defence-in-depth `assertRole` for
  destructive paths). Role-restricted pages redirect to `/devices`.
  401 from the API triggers a re-login; 403 raises a Spanish toast.
  User menu shows username + role badge.

- [ ] **0016 device-manuals-pdf** — *(extras, TODO)*
  Upload / list / view / delete PDF manuals attached to a device. Local
  Docker volume + Postgres metadata table (no MinIO yet). In-browser
  viewer.

- [ ] **0017 internal-greenhouse-map** — *(extras, TODO)*
  Per-`site_area` floor-plan image upload + drag-place devices (x,y in
  % of image). AI-generated plan recorded as a future enhancement, not
  a requirement.

## Phase 2+ — Later

Phase 2 (MQTT/CoAP/HTTP ingestion, realtime), Phase 3 (Superset, H2O,
Node-RED, NiFi, Airflow, MinIO at scale, Prometheus/Grafana) and
Kubernetes deployment are out of scope until Phase 1 closes.
