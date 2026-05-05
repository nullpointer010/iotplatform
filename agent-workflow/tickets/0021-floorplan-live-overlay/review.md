# Review — Ticket 0021

## What changed

Backend (`platform/api/`):
- `app/schemas_floorplans.py`: `PlacementOut` gains
  `device_state: str | None` and `primary_property: str | None`.
- `app/routes/floorplans.py`: helpers `_device_state_of` and
  `_primary_property_of`; both are populated in `list_placements`
  and `upsert_placement`. No new Orion calls.
- `tests/test_floorplans.py`: new
  `test_placements_include_state_and_primary_property`.

Frontend (`web/`):
- `src/lib/types.ts`: optional `device_state` and
  `primary_property` on `Placement`.
- `src/lib/marker-state.ts` (new): pure `classifyMarker` →
  `fresh-active | fresh-maintenance | inactive | stale | no-data`.
- `src/lib/marker-state.test.ts` (new): 6 cases.
- `src/app/sites/[siteArea]/use-live-overlay.ts` (new):
  `useQueries` fan-out, 30 s polling, paused while tab hidden,
  returns `Map<deviceId, LiveEntry>`.
- `src/app/sites/[siteArea]/live-marker.tsx` (new): tooltip-wrapped
  marker; palette per state; forwards drag handlers.
- `src/app/sites/[siteArea]/page.tsx`: imports above, replaces the
  old inline marker button with `<LiveMarker>`, mounts
  `<OverlayLegend>` below the floorplan.
- `src/i18n/messages/{en,es}.json`: `sites.overlay.*` keys.

## Acceptance criteria — evidence

- **A.1** `LiveMarker` colour set by `classifyMarker` → emerald
  (active) / amber (maintenance) / muted (inactive). See
  `STATE_CLS` in `live-marker.tsx`.
- **A.2** Marker pill shows `formatValue(live.value)` + unit (when
  present), or `—` when no live entry.
- **A.3** Stale = `now - lastSampleIso > STALE_AFTER_MS` (5 min,
  exported); marker uses the green hue at 40 % opacity + dashed
  border. `no-data` (no samples at all) renders muted + dashed.
- **A.4** `useQueries` runs every 30 s
  (`refetchInterval: 30_000`) with
  `refetchIntervalInBackground: false`, so polling pauses when
  the tab is hidden.
- **A.5** shadcn `Tooltip` with `delayDuration: 150`. Renders
  device name + `tooltipState` (i18n) + `tooltipProperty` + "hace
  X" via `formatDistanceToNowStrict`. Keyboard-accessible because
  `<TooltipTrigger asChild>` wraps a focusable `<button>`.
- **A.6** Drag handlers (`draggable`, `onDragStart`, `onDragEnd`)
  forwarded from the page to the marker root unchanged. The
  page's `onPlanDrop` handler is untouched.
- **A.7** `PlacementOut.device_state` / `primary_property` are
  populated from `_all_devices(orion)` already running in
  `list_placements`; no extra HTTP roundtrip.
- **A.8** RBAC unchanged: read = viewer, place = operator /
  manager, delete = admin (existing `Depends(require_roles(...))`
  decorators are untouched).
- **A.9** `sites.overlay.{tooltipState, tooltipProperty,
  tooltipUpdated, tooltipNoSamples, legendStale,
  deviceState.{active, maintenance, inactive, unknown}}` exist in
  both en.json and es.json.
- **A.10** `tests/test_floorplans.py::test_placements_include_state_and_primary_property`
  + `web/src/lib/marker-state.test.ts` (6 cases).
- **A.11** `make test` 184 passed; `npm run lint` clean; `npm test`
  23 passed.

## Follow-ups

- **FU1** Backend `/sites/{site_area}/live` aggregate: returns
  placements + last value per device in one call so the client
  doesn't fan out N queries per page load.
- **FU2** Streaming push (SSE / WebSocket) for the overlay.
- **FU3** Alert overlay (red marker when an alert is open) — owned
  by ticket 0022.
- **FU4** Filters on the overlay (by category / by property /
  by state).
- **FU5** Dark-mode tweaks for the palette (stale + no-data
  contrast on the dark theme).
- **FU6** Configurable per-device or per-site stale threshold
  (currently 5 min hard-coded).
- **FU7** When `controlledProperty` has more than one entry, allow
  the operator to pick which one drives the badge.

## Self-review notes

- The fan-out cap is implicit (one site has ≤ ~30 devices for the
  seed fleet); a hard cap is FU1.
- `useLiveOverlay` memoizes its return Map on a string signature
  built from each query's last `dateObserved`. This avoids
  re-rendering each marker every tick when nothing has changed.
- `LiveMarker` calls `classifyMarker` on each render; it's pure
  and cheap (no need to memoize).
- The `OverlayLegend` is purely decorative; it is not a follow-up
  surface for filters yet (FU4).
