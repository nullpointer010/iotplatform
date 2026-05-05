# Requirements — Device live state and charts

## Problem
The device detail page has three gaps that block actually using the
data the platform now ingests:

1. **No "Estado" tab.** Operators look at a device and see config
   metadata (Overview tab) and a raw telemetry table, but no
   at-a-glance "what is this device reporting *right now*". The
   backend already exposes `GET /api/v1/devices/{id}/state`; the UI
   just doesn't consume it.
2. **Telemetry tab is a flat table.** The `/telemetry` endpoint
   returns time-series, but the UI shows it as rows of timestamps.
   No chart, no time-range selector, no CSV export.
3. **`dataTypes` is invisible in the form.** The MQTT bridge needs
   `dataTypes` to validate payloads (0018b), but the device form
   only round-trips the field as a hidden JSON blob — operators
   can't actually edit it without going through the API.

## Goal
Three tightly coupled UI deliverables on the existing endpoints:

1. **Estado tab** on `/devices/[id]`: current value per attribute,
   `dateObserved`, freshness badge, 1 h / 24 h sparkline. Polling
   every 5–30 s.
2. **Telemetría tab v2**: real time-series chart over 24 h / 7 d /
   30 d windows, attribute selector, unit display, CSV export.
3. **`dataTypes` editor** in the MQTT section of the device form
   so operators can declare which `controlledProperty` is `Number`
   vs `Text` from the UI.

Plus a "Últimas medidas" card on the dashboard showing the most
recent reading per site.

## In scope
- `web/src/app/devices/[id]/state-tab.tsx` (new). Calls a new
  `api.getState(id)` helper that hits `GET /devices/{id}/state`.
  Polls with `useQuery` `refetchInterval` (default 15 s, configurable
  in code).
- Per-attribute card showing: value, unit (from device's
  `dataTypes` / `controlledProperty`), `dateObserved` ("hace 12 s"
  via `date-fns`), and a small sparkline of the last hour pulled
  from `/telemetry?lastN=…`.
- Freshness badge on each attribute: `fresh` (< 2 × poll interval),
  `stale` (older), `no-data` (null). Same thresholds reused on the
  floorplan in 0021.
- **Telemetría tab v2** rewrite using **Recharts** (new dependency).
  Time-range pills `24 h / 7 d / 30 d / custom`. Mapping: `fromDate`
  / `toDate` to the existing endpoint. Y-axis label = unit.
  CSV export button: client-side `Blob` download from the data
  already in memory (no new endpoint).
- **`dataTypes` editor** inside the MQTT section of
  `web/src/components/forms/device-form.tsx`: a small repeatable
  list of `(controlledProperty, "Number" | "Text")` rows, prefilled
  from the existing `dataTypes` map. The hidden JSON textarea is
  removed. The submit shape stays exactly the same (`dataTypes:
  {attr: "Number"}`), so the API contract is unchanged.
- Dashboard "Últimas medidas" card: top N (5) most recent telemetry
  rows across all devices in the current site. One reading per
  device-attribute. Reuses `/telemetry` per device — no new
  endpoint, but capped at the dashboard's already-loaded device
  list and only the device's first `controlledProperty`.
- i18n keys for everything new under existing `messages/*.json`.

## Out of scope
- WebSocket / SSE push. Polling only. A push-based ticket is
  filed as a follow-up.
- uPlot. Recharts is enough at expected fleet sizes; uPlot is
  reserved for a perf ticket if profiling justifies it.
- Server-side CSV export endpoint. Client-side only — fits the
  expected row counts (≤ 1000 per request).
- New backend endpoints. Everything reuses `/state` and
  `/telemetry`.
- Changes to the floorplan; that's 0021's job.
- `dataTypes` validation rules beyond what 0018b already enforces.

## User stories
- *As an operator*, I open a device and immediately see what it's
  reporting now and whether the values are fresh.
- *As an operator*, I can flip between "last 24 h", "last 7 d" and
  "last 30 d" of a single attribute on a chart, and download the
  underlying CSV without leaving the page.
- *As an admin*, I can declare in the device form that
  `temperature` is a `Number` and `mode` is `Text`, without editing
  raw JSON.
- *As any user*, the dashboard shows me the most recent live values
  across the fleet so I know the platform is alive.

## Acceptance criteria
- A.1 `/devices/[id]` has a new "Estado" tab between "Overview" and
  "Telemetría". It calls `GET /devices/{id}/state` every ~15 s.
- A.2 The Estado tab shows one card per `controlledProperty` with
  value, unit, `dateObserved` ("hace …") and a fresh/stale/no-data
  badge. It also surfaces top-level `deviceState`,
  `dateLastValueReported`, `batteryLevel` when present.
- A.3 Each Estado card shows a 1 h sparkline (no axes), built from
  `/telemetry?lastN=60`. Sparkline-only — no interactions.
- A.4 The Telemetría tab renders a Recharts line chart with axis
  labels, unit, and a tooltip on hover. Time-range pills `24 h /
  7 d / 30 d / custom` map to `fromDate` / `toDate`.
- A.5 Telemetría tab has a "Export CSV" button that downloads the
  currently displayed series as `<deviceId>_<attr>_<from>_<to>.csv`
  with header `dateObserved,numValue,unitCode`.
- A.6 The MQTT section of the device form exposes a `dataTypes`
  editor: add/remove rows, each row pairs a `controlledProperty`
  (string input or `Select` over the device's declared properties)
  with a type (`Number` / `Text`). Submitting produces the same
  `dataTypes` JSON the backend currently expects.
- A.7 The dashboard has a "Últimas medidas" card showing the 5
  most recent telemetry readings across the visible devices.
- A.8 No new backend route. `make test` (api) and `npm test` (web)
  stay green. New web tests cover the Estado tab freshness logic
  and the `dataTypes` editor round-trip.
- A.9 i18n: every new visible string has keys in `messages/es.json`
  and `messages/en.json`.

## Resolved decisions
- **Recharts** for charts. Already widely used in the React
  ecosystem, lightweight enough for the seed fleet, no canvas
  worker setup needed. uPlot can replace it later behind the same
  component prop.
- **Polling** instead of WebSockets. The simulator (0019b) emits
  every 10 s; a 15 s `refetchInterval` is plenty and avoids
  introducing a streaming endpoint and a new auth path.
- **Client-side CSV** because telemetry queries are already capped
  at 1000 rows server-side; no need for a streaming download.
- The `dataTypes` editor replaces (not augments) the hidden JSON
  field. Operators who used the JSON path are not blocked — the
  editor reads the existing JSON on edit and writes the same shape
  on save.
