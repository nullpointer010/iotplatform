# Ticket 0018a — workflow-docs-reconciliation

## Problem

The agent workflow has drifted away from the actual repository state.
Concretely:

1. **Ticket 0018 is closed but its paper trail is empty.**
   `tickets/0018-mqtt-broker-and-bridge/status.md` says `done` (closed
   2026-05-01) yet `tasks.md` still shows the original checklist with
   zero items ticked, and there is no `journal.md`/`review.md` content
   describing what was actually shipped.

2. **`roadmap.md` lies about Phase 2 progress.** It still lists 0018
   as `[ ] (Phase 2, blocker)` even though the broker, the bridge, the
   payload helpers, the `/system/mqtt` endpoint and the integration
   tests are all in `main`. Anyone reading the roadmap to plan the
   next ticket gets the wrong picture.

3. **`architecture.md` is frozen at ticket 0001.** It claims the API
   exposes only `GET /healthz`, the repo layout shows just
   `routes/health.py`, and the service stack has no Mosquitto, no
   Keycloak, no oauth2-proxy, no Postgres tables, no manuals volume.
   In reality 0003–0017 added all of that.

4. **A real ingestion bug hides behind the doc drift.** The MQTT
   bridge calls `OrionClient.patch_entity(device_id, attrs)` against
   the `Device:<id>` entity (`platform/api/app/mqtt_bridge.py:249`),
   while `GET /api/v1/devices/{id}/telemetry` queries QuantumLeap for
   entities of type `DeviceMeasurement` at
   `urn:ngsi-ld:DeviceMeasurement:<uuid>:<attr>`
   (`platform/api/app/routes/telemetry.py:76-79`). A real
   `mosquitto_pub` therefore moves `/state` and writes a row to
   CrateDB, but `/telemetry` returns empty. The "MQTT publish appears
   in `/telemetry`" promise of 0018 is **not** met. This must at
   least be recorded as known debt before any Phase 2 ticket builds
   on it.

5. **Phase 2 roadmap entries do not yet capture what we actually want
   to build next.** The user-supplied review listed concrete needs
   that have no home in the current roadmap text: expose `dataTypes`
   in the device form's MQTT section, embed the PDF viewer instead of
   `target="_blank"`, ship a real "Estado" tab with freshness and
   sparkline, ship real charts (Recharts/uPlot, 24 h / 7 d / 30 d,
   attribute selector, units, CSV export), keep alerts in Postgres
   (not in Orion), enumerate the alert catalog (stale, threshold,
   delta, stuck-sensor, low battery / RSSI, payload errors, overdue
   maintenance), add an MQTT sensor onboarding flow with a sample
   `mosquitto_pub`, and reserve the creative ideas (live-coloured
   greenhouse map, 24 h replay over the floor plan, sensor health
   score, event annotations) so they are not lost.

## Goal

Bring the workflow docs back in sync with reality, file the runtime
fix as a properly scoped follow-up ticket, and rewrite the Phase 2
roadmap so every item the user just enumerated has an explicit home.
**No runtime code changes in this ticket.**

## User stories

- As the agent on the next session, I want `roadmap.md`,
  `architecture.md` and ticket 0018's metadata to match `main`, so
  that I plan the next ticket from facts instead of stale stubs.
- As the user reviewing the plan, I want every concrete item I just
  raised (dataTypes form, embedded PDF viewer, live state, charts,
  alert catalog, onboarding, system health, creative ideas) to be
  visible in the roadmap, so nothing silently disappears.
- As any contributor, I want the `Device` vs `DeviceMeasurement`
  ingestion gap recorded both as a roadmap blocker (0018b) and as a
  `memory/gotchas.md` entry, so the trap does not bite again.

## Acceptance criteria (verifiable)

### A. Reconcile ticket 0018
- [ ] `tickets/0018-mqtt-broker-and-bridge/tasks.md`: every checkbox
      that corresponds to code already in `main` is ticked; any
      checkbox that was **not** delivered (notably "MQTT publish lands
      in `/telemetry`") is left unticked and annotated
      `→ moved to 0018b`.
- [ ] `tickets/0018-mqtt-broker-and-bridge/journal.md` contains a
      dated entry summarising what shipped, what did not, and the
      `Device` vs `DeviceMeasurement` gap.
- [ ] `tickets/0018-mqtt-broker-and-bridge/review.md` self-review
      section is filled (what changed, why ACs were partially met,
      debt introduced, follow-ups: 0018b).

### B. Reconcile `roadmap.md`
- [ ] 0018 is marked `[x] (done 2026-05-01)` with a one-paragraph
      "what shipped / what did not" summary that names the
      `DeviceMeasurement` gap.
- [ ] A new entry **0018b telemetry-ingest-canonicalization** is
      inserted right after 0018 as the new Phase 2 blocker. Scope:
      every successful MQTT (and later HTTP) ingest must, in addition
      to patching `Device:<id>` (state + `dateLastValueReported`),
      upsert `urn:ngsi-ld:DeviceMeasurement:<deviceUuid>:<attr>` with
      `numValue`, `dateObserved`, `unitCode`, `refDevice`,
      `controlledProperty`. Verifiable: publish via MQTT and observe
      both `/state` and `/telemetry?controlledProperty=...` reflect
      the value.
- [ ] Existing 0019–0028 entries are rewritten so the user-supplied
      items have an explicit home **without renumbering** anything
      already on disk. Concretely:
    - **0019 http-ingest-endpoint** keeps its scope and explicitly
      mentions the LoRaWAN webhook flavour (Chirpstack/TTN) plus the
      per-device API key table.
    - **0020 device-live-state-and-charts** is expanded to require:
      (a) a real "Estado" tab with last value per attribute,
      timestamp, freshness badge ("sin datos desde X") and a 1 h /
      24 h sparkline, polling every 5–30 s; (b) Recharts (or uPlot)
      time-series with 24 h / 7 d / 30 d range selector, attribute
      selector, unit display and CSV export; (c) a `dataTypes` editor
      in the MQTT section of the device form (today only present in
      conversion code, not in the UI).
    - **0021 floorplan-live-overlay** stays as the polling overlay.
    - **0022 alerts-and-rules** is expanded to state explicitly that
      rules, events, ack, closure, severity and audit live in
      Postgres (not Orion); Orion may optionally mirror
      `alertStatus` / `activeAlertCount` for FIWARE consumers. The
      built-in rule catalog must cover: no-data-for-X-minutes,
      threshold (e.g. `temperature > 35`, `humidity < 40`), abrupt
      delta (`Δtemperature > N °C in 10 min`), stuck sensor (no
      variance for hours), low battery, low RSSI/SNR, payload errors,
      and overdue / too-long maintenance.
    - **0023 actuator-commands** keeps scope (deferred concern; not a
      v1 blocker).
    - **0024 audit-log** keeps scope.
    - **0025 csv-import-export** keeps scope.
    - **0026 system-health-page** is reaffirmed as the explicit
      replacement for `/healthz`, covering Orion, QuantumLeap,
      CrateDB, Postgres, Mosquitto and Keycloak.
    - **0027 backups-and-restore** keeps scope.
    - **0028 prod-edge-tls** keeps scope.
    - **0029 operator-handbook** is reframed as a sensor-onboarding
      flow (credentials, topic, sample `mosquitto_pub`, payload-test
      console) plus the operator docs originally listed.
- [ ] A new "Phase 2 stretch — creative" section captures, as
      explicit but un-numbered candidates: live-coloured greenhouse
      map (color by temperature / humidity / staleness / alert), 24 h
      timeline replay over the floor plan, sensor health score
      (freshness + battery + noise + outliers + maintenance), and
      event annotations on charts ("opened windows", "irrigation",
      "treatment").
- [ ] The "Re-plan" block at the end of Phase 1 gets a 2026-05-05
      sub-block recording this reconciliation and pointing at 0018a.

### C. Reconcile `architecture.md`
- [ ] Repo layout reflects what is in `main`: at minimum
      `platform/api/app/{config,deps,errors,ngsi,orion,quantumleap,
      mqtt_bridge,mqtt_payload,...}.py`,
      `platform/api/app/routes/{health,devices,telemetry,maintenance,
      operation_types,manuals,me,system,...}.py`,
      `platform/api/alembic/`, `platform/config/{mosquitto,keycloak,
      cratedb}/`, `web/`.
- [ ] Service stack table adds: `mosquitto`, `keycloak`,
      `keycloak-db`, `oauth2-proxy`, and notes that `iot-api` no
      longer publishes a host port (single-origin edge from 0013b).
- [ ] The "API runtime" section replaces "Single endpoint so far:
      `GET /healthz`" with a concise inventory of the route groups
      actually mounted (devices, telemetry, state, maintenance log,
      operation types, manuals, me, system/mqtt, healthz) without
      duplicating `backend.md`.
- [ ] A new "Auth" subsection mentions Keycloak realm `iot-platform`,
      4 realm roles, oauth2-proxy as the only host-facing port, and
      JWT validation in FastAPI.
- [ ] A new "Ingestion (current)" subsection states the **known
      gap**: the MQTT bridge currently updates `Device` only;
      `DeviceMeasurement` upsert is tracked in 0018b.

### D. Memory
- [ ] `agent-workflow/memory/gotchas.md` gets a one-line entry:
      "`/telemetry` reads `DeviceMeasurement`, not `Device` attrs.
      Any new ingestion path must upsert
      `urn:ngsi-ld:DeviceMeasurement:<deviceUuid>:<attr>` (with
      `numValue`, `dateObserved`, `unitCode`, `refDevice`) in
      addition to (or instead of) patching the `Device`."
- [ ] `agent-workflow/memory/gotchas.md` gets a second entry:
      "Closing a ticket without ticking `tasks.md` and filling
      `journal.md`/`review.md` desyncs the workflow. Always run the
      reconciliation checklist before flipping `status.md` to `done`."
- [ ] No new entry in `patterns.md` or `glossary.md` unless the
      design surfaces one.

## Out of scope

- Any runtime code change. Specifically: **do not** modify
  `mqtt_bridge.py`, `telemetry.py`, the device form, the manuals tab,
  the system health route, or any test. Those land in 0018b and
  later.
- Renumbering or deleting existing tickets on disk (0018–0029 keep
  their numbers).
- Implementing any of the creative-stretch ideas; they are only
  recorded.

## Resolved decisions (user said "Default" 2026-05-05)

- **Q1 → 0018b is MQTT-only.** 0019 (HTTP/LoRaWAN webhook ingest) is
  written to reuse the same canonical writer introduced by 0018b.
- **Q2 → Recharts** for 0020. uPlot reserved for a later perf ticket
  if profiling justifies it.
- **Q3 → in-process** evaluator for 0022 v1; extraction to a worker
  container is a later ticket if it proves necessary.
- **Q4 → new ticket 0029b embedded-pdf-viewer** is added to the
  roadmap (replaces the current `target="_blank"` jump in
  `web/src/components/devices/manuals-tab.tsx`). Independent from
  the onboarding work in 0029.

Acceptance criterion B is therefore extended: roadmap must also list
**0029b embedded-pdf-viewer** under Phase 2.
