# Ticket 0022 — alerts-and-rules

## Problem

Today the platform has no notion of "something is wrong". Operators
must eyeball `/sites/[siteArea]` (0021) or telemetry charts (0011)
to spot a stuck sensor, a temperature excursion, or a device that
stopped reporting. The roadmap (Phase 2) calls for per-device
threshold rules, an alerts inbox, and the supporting state machine
(open → ack → close) so the team can respond to incidents instead
of polling the UI.

Alert state is intrinsically transactional and historical
(`opened_at`, `closed_at`, `ack_by`, audit trail), so it belongs in
Postgres alongside `maintenance_log` and `device_ingest_keys`, not
in Orion. Orion stays the current-context source.

## Goal

Add a Postgres-backed alert engine to `iot-api` with a built-in
rule catalog, an in-process evaluator that consumes telemetry +
device state, and a web inbox at `/alerts` with ack / close /
per-device badge.

## User stories

- As an **operator**, I want to see all open alerts on `/alerts`
  with severity, device, rule, opened-at and last sample, so I can
  triage incidents quickly.
- As an **operator**, I want to **acknowledge** an alert (so my
  teammates know it's being handled) and then **close** it once
  resolved.
- As a **manager**, I want to define rules per device or per
  device-attribute (threshold, no-data, abrupt delta, stuck,
  battery, RSSI, payload-error rate, overdue maintenance) without
  touching code.
- As a **viewer**, I want to *read* the alert inbox and per-device
  alert badge but not modify anything.
- As an **admin**, I want to delete obsolete rules and old closed
  alerts.
- As an external FIWARE consumer, I want to read `alertStatus` and
  `activeAlertCount` on the `Device` entity in Orion (mirror) so I
  can drive my own dashboards without querying Postgres.

## Acceptance criteria (verifiable)

### Data model
- [ ] **A.1** New Alembic migration `0005_alerts_and_rules.py`
  creates two tables in Postgres:
  - `alert_rules(id uuid pk, name text, device_id uuid null,
    attribute text null, kind text not null, params jsonb not null,
    severity text not null check in ('info','warning','critical'),
    enabled bool default true, created_at timestamptz, updated_at
    timestamptz)`. `device_id null` ⇒ rule applies to **all**
    devices; `attribute null` ⇒ kind doesn't need an attribute
    (e.g. `no-data`, `low-battery`).
  - `alerts(id uuid pk, rule_id uuid fk, device_id uuid not null,
    opened_at timestamptz, closed_at timestamptz null, ack_at
    timestamptz null, ack_by text null, severity text, summary
    text, payload jsonb)`. Index on `(device_id, closed_at)` and
    `(opened_at desc)`.
- [ ] **A.2** A rule may not be deleted while it has open alerts;
  the API returns `409 Conflict` with `code: "rule-has-open-alerts"`.
  Closed alerts retain `rule_id` (set on `ON DELETE SET NULL` once
  the rule is gone) so historical rows remain readable.

### Rule catalog (kinds + JSON params)
- [ ] **A.3** Eight kinds, each with a documented `params` schema
  (Pydantic `RuleParams<Kind>` discriminated by `kind`):
  - `threshold` — `{op: ">"|"<"|">="|"<=", value: float}`
    (requires `attribute`).
  - `no-data` — `{minutes: int}` (per device or per
    `(device, attribute)`).
  - `abrupt-delta` — `{delta: float, window_minutes: int}`
    (requires `attribute`).
  - `stuck` — `{hours: int}` (no variance for N hours; requires
    `attribute`).
  - `low-battery` — `{percent: int}` (uses `batteryLevel`
    convention).
  - `low-rssi` — `{dbm: int}` (uses `rssi` convention).
  - `payload-error-rate` — `{rate: float, window_minutes: int}`
    (sustained `dropped_invalid` / total ratio above `rate`).
  - `overdue-maintenance` — `{days: int}` (no maintenance entry in
    last N days for that device).
- [ ] **A.4** Rejected combos return `422` with a clear message
  (e.g. `threshold` without `attribute`).

### Evaluator
- [ ] **A.5** Single in-process evaluator (`app/alerts/evaluator.py`)
  triggered (a) on every successful `POST /devices/{id}/telemetry`
  for value-driven kinds (`threshold`, `abrupt-delta`, `stuck`,
  `low-battery`, `low-rssi`, `payload-error-rate`), and (b) on a
  periodic tick (every 60 s, started in `app/main.py` lifespan) for
  time-driven kinds (`no-data`, `overdue-maintenance`).
- [ ] **A.6** Evaluator is **idempotent**: opening an alert when
  one is already open for `(rule_id, device_id)` is a no-op.
  Closing follows the same key.
- [ ] **A.7** Auto-close: when the underlying condition clears
  (e.g. value back below threshold; data starts flowing again),
  the evaluator sets `closed_at = now`. Manual close (operator)
  also sets `closed_at`.
- [ ] **A.8** The periodic tick survives evaluator errors per
  device (one bad rule must not stop the loop) and logs the
  failure with `device_id` + `rule_id`.

### API
- [ ] **A.9** New router `app/routes/alerts.py` mounted under
  `/api/v1`:
  - `GET /alert-rules` — viewer.
  - `POST /alert-rules` — manager.
  - `PATCH /alert-rules/{id}` — manager (toggle enabled, change
    params/severity).
  - `DELETE /alert-rules/{id}` — admin.
  - `GET /alerts?status=open|all&device_id=&severity=&limit=&offset=`
    — viewer; default `status=open`, `limit=50`, ordered
    `opened_at desc`.
  - `POST /alerts/{id}/ack` — operator (records `ack_by` from
    JWT preferred-username).
  - `POST /alerts/{id}/close` — operator (manual close).
  - `DELETE /alerts/{id}` — admin (closed alerts only; deleting an
    open alert returns `409`).
- [ ] **A.10** `GET /devices/{id}` response gains `active_alert_count`
  and `alert_status: "ok"|"warning"|"critical"` (max severity of
  open alerts). Computed in the route, not stored. Source of truth
  remains Postgres; this is a convenience join for the UI.

### Orion mirror
- [ ] **A.11** When an alert opens or closes, the evaluator
  upserts two attributes on the device entity in Orion:
  `alertStatus` (`"ok"|"warning"|"critical"`) and `activeAlertCount`
  (int). Failures to write Orion are logged and do **not** block
  the Postgres state change (Postgres is the source of truth).

### Web — inbox + badge
- [ ] **A.12** New page `/alerts` lists open alerts with: severity
  pill, device link, rule name, "abierta hace X" (date-fns), last
  value/unit if applicable, ack and close buttons (gated). Empty
  state with i18n copy.
- [ ] **A.13** Filters: `status` (open|all), `severity`,
  `device` (free-text). 30 s polling via react-query.
- [ ] **A.14** Per-device alert badge on `/devices`, `/devices/[id]`
  header, and as a small red ring on `LiveMarker` (extends 0021
  classifier without changing its existing 5-state taxonomy — the
  ring is a separate visual layer).
- [ ] **A.15** Rules editor at `/alerts/rules` (manager+) with a
  table + create/edit dialog. Fields are per-kind via a
  discriminated form (the dialog shows only the inputs relevant to
  the selected `kind`).
- [ ] **A.16** RBAC — UI gating mirrors the API matrix:
  - viewer: read inbox + read rules.
  - operator: ack + close.
  - manager: create / edit / toggle rules.
  - admin: delete rules + delete closed alerts.
- [ ] **A.17** i18n keys under `alerts.*` and `alerts.rules.*` in
  both `en.json` and `es.json`.

### Tests
- [ ] **A.18** Backend tests in `tests/test_alerts.py` cover:
  rule CRUD + RBAC, each of the 8 kinds opening + auto-closing
  exactly once on the seeded fleet, idempotency under repeated
  telemetry, ack/close transitions, `409` on
  delete-rule-with-open-alerts, `409` on
  delete-open-alert.
- [ ] **A.19** Web vitest covers the rule-form discriminated render
  (each `kind` shows the right inputs) and the inbox list rendering
  (open vs closed, severity styling).
- [ ] **A.20** `make test` and `npm test` pass; `npm run lint` and
  `tsc --noEmit` clean.

## Out of scope

- Webhook / email / Telegram notifications. **In-app only** for v1;
  external delivery is a follow-up ticket.
- Extracting the evaluator into its own worker container. Stays
  in-process inside `iot-api`.
- Snooze / mute schedules per rule.
- Multi-condition / boolean-combined rules (AND/OR of two kinds).
- Per-tenant or per-site rule scoping (rules are global or
  per-device for v1).
- Graphing the alert timeline on the device telemetry page.
- Audit log integration — that's ticket **0024**. Alerts
  ack/close are still recorded inline in `alerts` (`ack_by`,
  `closed_at`) but no separate `audit_events` row is written here.

## Open questions \u2014 resolved 2026-05-05

1. **Evaluator trigger**: synchronous inside `POST /devices/{id}/telemetry`
   (default).
2. **Periodic tick**: env-configurable via `ALERTS_TICK_SECONDS`,
   default `60`.
3. **Orion mirror** of `alertStatus` / `activeAlertCount`: in scope
   (default).
4. **Default rule seeding**: seed a small Almer\u00eda starter set
   (`no-data > 30 min` per device, `low-battery < 15 %`).
5. **`payload-error-rate` data source**: default \u2014 add lightweight
   per-device rolling counters in Postgres as part of this ticket.
6. **`stuck`-sensor variance check**: exact equality across the
   window (default).
