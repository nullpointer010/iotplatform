# 0021 — floorplan-live-overlay

## Why
Today `/sites/[siteArea]` only shows where each device sits on the
floorplan. Operators have to click into each marker to learn whether
it is alive and what value it is reporting. We want the floorplan to
double as a live overview: at a glance, which devices are healthy,
which are in maintenance / inactive, and what numeric value the
primary `controlledProperty` is currently showing.

This builds on:
- 0017 (`DevicePlacement` table + drag/drop UI on the floorplan).
- 0020 (live `/state` and per-attribute polling pattern).
- 0004 (`/telemetry?lastN=1` for the latest sample).

## What

### Acceptance criteria

- **A.1** On `/sites/[siteArea]`, each placed marker is colour-coded
  by `deviceState`:
    - `active` → green,
    - `maintenance` → amber,
    - `inactive` (or unknown) → grey.
- **A.2** Each marker shows the latest numeric value of the primary
  `controlledProperty` (the first entry in the device's
  `controlledProperty` array) as a small badge inside the marker,
  with the unit suffix when known. Non-numeric primary properties
  show "—".
- **A.3** A marker whose latest sample is older than **N = 5 min**
  shows a "stale" visual cue (dashed border + lighter fill). A
  device with no sample at all is also rendered as stale-grey.
- **A.4** The overlay polls every **30 s** while the page is
  visible; pauses when `document.hidden`. Polling reuses the
  existing endpoints — no new API surface for the client.
- **A.5** Hovering / focusing a marker shows a tooltip with:
  device name, deviceState label, primary property name, value +
  unit, and "hace X" timestamp. Tooltip is keyboard-accessible.
- **A.6** Drag-and-drop placement (0017 behaviour) keeps working,
  including for placed markers being repositioned. Polling does
  not interfere with drags in progress.
- **A.7** Backend: extend `PlacementOut` with `device_state` and
  `primary_property` (first `controlledProperty`), populated from
  the same `_all_devices(orion)` call already happening in
  `list_placements`. No extra Orion round-trip.
- **A.8** RBAC unchanged: viewer can read overlay, operator /
  maintenance_manager can still place / move markers, admin can
  still delete placements and the floorplan.
- **A.9** New visible strings have keys in `i18n/messages/{en,es}.json`.
- **A.10** Tests:
    - API: extend `tests/test_floorplans.py` with one case asserting
      that `device_state` and `primary_property` flow through
      `list_placements` for placed and unplaced devices.
    - Web: pure unit test for the marker-state classifier
      (`fresh-active | fresh-maintenance | inactive | stale | no-data`).
- **A.11** `make test` (api) and `npm run lint && npm test` (web)
  green.

### Out of scope (follow-ups)

- A backend `/sites/{site_area}/live` aggregate that returns
  placements + last value per device in one call (replaces the
  N-fan-out from the client). Tracked as a follow-up.
- Streaming push (SSE / WebSocket).
- Alert overlay (red marker when an alert is open). Belongs to
  ticket 0022.
- Device-level filtering (by category, by property) on the overlay.
- Dark-theme tweaks for the marker palette.

## Notes / assumptions
- Numeric badge fan-out: the client issues one
  `getTelemetry({lastN: 1})` per placed device, like the
  dashboard "Últimas medidas" card. Capped by the size of one
  site; we expect ≤ ~30 placed devices per site for the seed
  fleet.
- "Primary property" = first element of the device's
  `controlledProperty` list. If a device has no
  `controlledProperty`, no badge is rendered.
- Stale threshold (5 min) is a UI constant; configurability is a
  follow-up.
- Marker sizing stays the same (small pill) — colour and dashed
  border carry the state, not size.
