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

### Re-plan (2026-05-05) — workflow/docs reconciliation (0018a)

Audit revealed three drifts: ticket 0018 closed with an empty
`tasks.md`, the roadmap still listed it as TODO, and `architecture.md`
was frozen at ticket 0001. A fourth, runtime drift surfaced in the
process: the MQTT bridge updates the `Device` entity, but `/telemetry`
reads `DeviceMeasurement` entities — so a real `mosquitto_pub` moves
`/state` but does not appear in `/telemetry`. Ticket **0018a**
reconciles the docs (this entry, the 0018 paper trail, and
`architecture.md`) and files **0018b
telemetry-ingest-canonicalization** as the new Phase 2 blocker.
During the same audit the user-supplied scope notes were absorbed
into the existing 0019–0029 entries (no renumbering): a `dataTypes`
editor in the device form's MQTT section and a real "Estado" tab
(freshness + sparkline) join 0020; the full alert catalog (no-data,
threshold, delta, stuck, battery, RSSI, payload errors, overdue
maintenance) and the Postgres-as-truth / optional Orion mirror
clarification join 0022; sensor onboarding (credentials, topic,
sample `mosquitto_pub`, payload-test) joins 0029; the embedded PDF
viewer becomes new ticket **0029b**; four creative ideas live in a
new "Phase 2 stretch — creative" subsection.
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

- [x] **0016 device-manuals-pdf** — *(done 2026-04-30)*
  Upload / list / view / delete PDF manuals attached to a device. Local
  Docker volume + Postgres metadata table (no MinIO yet). In-browser
  viewer.

- [x] **0017 internal-greenhouse-map** — *(done 2026-05-01)*
  Per-`site_area` floor-plan image upload + drag-place devices (x,y in
  % of image). AI-generated plan recorded as a future enhancement, not
  a requirement.

## Phase 2 — "Devices actually talk"

Phase 1 closed with a polished **metadata catalog** but nothing is
ingesting real telemetry; every measurement today comes from
`make seed`. Phase 2 turns the platform into something a greenhouse
operator can actually deploy: real ingestion, live visibility, alerts,
actuators, and basic operability (audit, health, backups, prod TLS).

Ordering rationale: ingestion first (without it nothing else means
anything), then make the data visible (charts, live overlay), then
close the loop (alerts, commands), then operability and docs.

- [x] **0018 mqtt-broker-and-bridge** — *(done 2026-05-01; partial)*
  Eclipse Mosquitto in Compose (password-file auth, no TLS, loopback
  only), in-process `MqttBridge` worker inside `iot-api` subscribing
  to `<mqttTopicRoot>/+` per MQTT-enabled device, payload validation
  against `dataTypes`, `GET /api/v1/system/mqtt` admin stats, and 16
  unit + 7 integration tests. **What did not ship:** the bridge
  patches the `Device` entity, so `/state` updates but
  `/telemetry` (which reads `DeviceMeasurement`) stays empty. That
  promise moves to 0018b.

- [x] **0018b telemetry-ingest-canonicalization** — *(Phase 2, blocker)*  *(done 2026-05-05)*
  Make the MQTT bridge canonical against the data model pinned in
  0002. On every successful publish, in addition to patching
  `Device:<id>` (state + `dateLastValueReported`), upsert
  `urn:ngsi-ld:DeviceMeasurement:<deviceUuid>:<attr>` with
  `numValue`, `dateObserved`, `unitCode`, `refDevice` and
  `controlledProperty`. Reuse the existing `dataTypes` validation;
  do not re-architect the bridge. Verifiable: a real `mosquitto_pub`
  moves both `/state` *and*
  `/telemetry?controlledProperty=<attr>`. 0019 (HTTP/LoRaWAN ingest)
  is written to reuse the same canonical writer.

- [x] **0019 http-ingest-endpoint** — *(Phase 2)*  *(done 2026-05-05)*
  `POST /api/v1/devices/{id}/telemetry` with a small JSON body, for
  HTTP-only sensors and LoRaWAN webhook bridges (Chirpstack / TTN).
  Validated against `dataTypes`. Auth via a service-account JWT or a
  per-device static API key (new `device_ingest_keys` table) — kept
  off the user-RBAC ladder so a sensor never needs a Keycloak account.
  Reuses the canonical `DeviceMeasurement` writer introduced in
  0018b (no second ingestion shape).

- [x] **0019b live-ingest-simulator** — *(Phase 2)*  *(done 2026-05-05)*
  In-process background task in `iot-api`, gated by `SIMULATOR_ENABLED`
  (default true in compose). Walks every registered device every
  ~10 s and publishes a realistic random-walk value per
  `controlledProperty` through the device's declared protocol:
  paho `PUBLISH` to Mosquitto for MQTT, loopback
  `POST /telemetry` with `X-Device-Key` for HTTP. Devices on
  protocols we don't yet have an adapter for (LoRaWAN, PLC, Modbus,
  CoAP) are PATCHed to `deviceState="maintenance"` once. Result:
  `make up` (+ optionally `make seed`) → live data in `/state` and
  `/telemetry` for the entire fleet, with zero extra commands.

- [x] **0020 device-live-state-and-charts** — *(Phase 2, done 2026-05-05)*
  Three tightly-coupled deliverables, all on top of the endpoints
  shipped in 0004 and the canonical ingest from 0018b:
  1. **Estado tab** on the device detail page: current value per
     attribute, `dateObserved` timestamp, freshness badge
     ("sin datos desde X") and a 1 h / 24 h sparkline. Polling every
     5–30 s; WebSocket/SSE deferred to a follow-up.
  2. **Telemetría tab**: real time-series with **Recharts** over
     24 h / 7 d / 30 d, attribute selector, unit display, **CSV
     export**. uPlot is reserved for a later perf ticket if profiling
     justifies it.
  3. **`dataTypes` editor** in the MQTT section of the device form
     (`web/src/components/devices/device-form.tsx`). Today the field
     is converted to/from JSON in code but not exposed to the user;
     without it, payload validation is impossible to configure from
     the UI.
  Dashboard also gets a "Últimas medidas" card per site. No new
  endpoints.

- [x] **0021 floorplan-live-overlay** — *(Phase 2, done 2026-05-05)*
  On `/sites/[siteArea]`, fetch each placed device's last value and
  state and color-code the marker (active / maintenance / inactive +
  numeric badge for the primary `controlledProperty`). 30 s polling,
  "stale" pill if `> N min` since last sample. Reuses 0017 placements.

- [x] **0021a telemetry-pagination-and-date-format** — *(Phase 2 fix, done 2026-05-05)*
  Telemetry GET capped at 100 even with `lastN=1000` (forwarded
  `limit` overrode `lastN`). Custom range used native
  `<input type=datetime-local>` whose format follows browser/OS
  locale. Fixed both, plus added 100/page client-side pagination
  for the raw-data table.

- [ ] **0022 alerts-and-rules** — *(Phase 2)*
  Per-device threshold rules in Postgres. Rules, events, ack,
  closure, severity and audit **live in Postgres** (not in Orion);
  Orion remains the current-context source. Optionally mirror
  `alertStatus` and `activeAlertCount` onto the `Device` entity in
  Orion so other FIWARE consumers see the same signal. A small
  evaluator runs **in-process** inside `iot-api` for v1
  (extraction to a worker container is a later ticket if needed),
  raising rows in `alerts(device_id, rule_id, opened_at, closed_at,
  ack_by, severity)`. Built-in rule catalog (configurable per
  device/attribute):
    - **no-data-for-X-minutes** (per device/attribute);
    - **threshold** (e.g. `temperature > 35`, `humidity < 40`);
    - **abrupt delta** (e.g. Δ`temperature` > N °C in 10 min);
    - **stuck sensor** (no variance for N hours);
    - **low battery**;
    - **low RSSI / SNR**;
    - **payload errors** (sustained `dropped_invalid` rate);
    - **overdue maintenance** / **device too long in maintenance**.
  Web inbox at `/alerts` and a per-device alert badge. RBAC: viewer
  reads, operator acks, manager configures rules, delete = admin.
  Notifications limited to in-app for now (webhook / email deferred
  to a follow-up).

- [ ] **0023 actuator-commands** — *(Phase 2)*
  UI + endpoint to send a write command: MQTT publish on the device's
  `mqttTopicRoot/cmd` subtopic, or PATCH an Orion attribute that an
  external runtime listens to (PLC write deferred to a later ticket).
  Recorded in the audit log (0024). Operator+ only.

- [ ] **0024 audit-log** — *(Phase 2)*
  `audit_events(id, ts, actor, role, method, path, target_id, summary)`
  table populated by a FastAPI middleware on every state-changing
  route. Admin-only `/audit` page with filtering by actor / target /
  date. No retention policy yet.

- [ ] **0025 csv-import-export** — *(Phase 2)*
  Bulk CSV upload of devices (dry-run + partial-success report,
  manager+) and CSV/JSON export of telemetry over a chosen date range
  (viewer+). Streamed responses to keep memory flat on big exports.

- [ ] **0026 system-health-page** — *(Phase 2)*
  `GET /api/v1/system/health` aggregates a ping per upstream (Orion,
  QuantumLeap, CrateDB, Postgres, Mosquitto, Keycloak) with latency
  and a coarse status. Admin-only `/system` page. **Replaces** the
  current single `/healthz` as the operability surface. The existing
  `/system/mqtt` from 0018 stays as a finer-grained drill-down.

- [ ] **0027 backups-and-restore** — *(Phase 2)*
  `make backup` snapshots Postgres + Mongo (Orion) + Crate + the
  manuals/floorplans Docker volume into a timestamped tarball.
  `make restore TARBALL=...` reverses it. Documented procedure;
  cron'd backup deferred.

- [ ] **0028 prod-edge-tls** — *(Phase 2)*
  Production Compose profile with Caddy or Traefik in front of
  oauth2-proxy doing Let's Encrypt + HTTP→HTTPS. Secrets moved to
  env-or-file. New `make up-prod` target. Still single-host; HA and
  Kubernetes are Phase 3.

- [ ] **0029 sensor-onboarding-and-handbook** — *(Phase 2)*
  Reduce friction to attach a real sensor: a guided **MQTT sensor
  onboarding** flow in the UI that, given a device, surfaces the
  bridge credentials, the per-attribute topic, a copy-paste
  `mosquitto_pub` example with a sample JSON payload, and a
  payload-test console that shows the parsed value, the inferred
  NGSI type and any `dataTypes` validation error before going live.
  Plus end-user docs under `docs/`: "onboard an MQTT sensor",
  "create a maintenance plan", "configure an alert", "interpret
  the floor plan". Linked from `README.md`. Spanish primary,
  English secondary (matches the i18n direction).

- [ ] **0029b embedded-pdf-viewer** — *(Phase 2)*
  Replace the `target="_blank"` jump in
  `web/src/components/devices/manuals-tab.tsx` with an in-platform
  PDF viewer (e.g. `<iframe>` against the existing inline-download
  endpoint from 0016, or `react-pdf` if a richer reader is needed).
  No new backend; the viewer reuses the manuals API.

### Phase 2 stretch (only if time permits)

- [ ] **0030 multi-site-rbac** — Per-`site_area` role grants on top of
  the global Keycloak roles. A user can be `operator` on
  `IFAPA - Invernadero 1` but only `viewer` everywhere else.
- [ ] **0031 plc-modbus-bridge** — Equivalent of 0018 but for Modbus
  TCP, polling at `plcReadFrequency` and mapping `plcTagsMapping` →
  Orion attributes.

### Phase 2 stretch — creative (un-numbered, captured 2026-05-05)

Ideas surfaced during the 0018a audit. Not scheduled; recorded so
they are not lost when the corresponding base ticket lands.

- **Live-coloured greenhouse map** — extend the 0021 floor-plan
  overlay with per-marker colour by `temperature` / `humidity` /
  staleness / open-alert severity. Natural extension of 0021 once
  0020 charts are in.
- **24 h timeline replay** over the floor plan — scrubber that
  re-plays the last N hours of telemetry on top of the same overlay.
  Builds on 0020 (time-series query) + 0021 (overlay).
- **Sensor health score** — a 0–100 score per device combining
  freshness, battery, noise, outlier rate and maintenance state.
  Surfaced as a column on the devices list and a badge on the
  detail page. Builds on 0022 (alert signals).
- **Event annotations on charts** — user-marked events
  ("abrimos ventanas", "riego", "tratamiento") rendered as vertical
  guides on the 0020 charts so the impact on the time-series is
  visible. Storage in Postgres alongside alerts.

## Phase 3+ — Later

Phase 3 lands the analytics / automation layer (Apache Superset,
H2O.ai, Node-RED, Apache NiFi, Apache Airflow, MinIO at scale,
Prometheus / Grafana) and Kubernetes deployment. Out of scope until
Phase 2 closes.
