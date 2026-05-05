# Design — 0021 floorplan-live-overlay

## Backend

### `PlacementOut` (extend)
`platform/api/app/schemas_floorplans.py`

```python
class PlacementOut(BaseModel):
    device_id: UUID
    name: str | None
    x_pct: float | None
    y_pct: float | None
    device_state: str | None        # NEW
    primary_property: str | None    # NEW
```

### `list_placements` (extend)
`platform/api/app/routes/floorplans.py`

The handler already iterates `_all_devices(orion)` filtered by
`_site_area_of(d) == site_area`. For each `d`, also read:

- `device_state` ← `d.get("deviceState", {}).get("value")`
  (Orion attribute object shape).
- `primary_property` ← first element of
  `d.get("controlledProperty", {}).get("value")` when the value is
  a non-empty list; otherwise `None`.

Both helpers go alongside `_site_area_of` in `floorplans.py` so the
shape-defensiveness lives in one place. No extra Orion calls.

### Tests
- Add `test_list_placements_returns_state_and_primary_property` in
  `platform/api/tests/test_floorplans.py`. Use the existing
  `httpx_mock` Orion stub style: one device with `deviceState=active`
  + `controlledProperty=["temperature","humidity"]`, one with
  neither. Assert the response contains the two new fields and that
  `primary_property` is `"temperature"` for the first and `None`
  for the second.

## Frontend

### Types
`web/src/lib/types.ts` — extend `Placement`:

```ts
export interface Placement {
  device_id: string;
  name: string | null;
  x_pct: number | null;
  y_pct: number | null;
  device_state?: string | null;
  primary_property?: string | null;
}
```

(Optional fields keep the existing test data and consumer code
backwards-compatible.)

### State classifier (pure)
`web/src/lib/marker-state.ts` (new):

```ts
export type MarkerState =
  | "fresh-active"
  | "fresh-maintenance"
  | "inactive"
  | "stale"
  | "no-data";

export function classifyMarker(input: {
  deviceState: string | null | undefined;
  lastSampleIso: string | null | undefined;
  staleAfterMs?: number; // default 5 * 60_000
  now?: number;
}): MarkerState;
```

Rules (in order):
1. No `lastSampleIso` → `no-data`.
2. Age > `staleAfterMs` → `stale` (regardless of state).
3. `deviceState === "maintenance"` → `fresh-maintenance`.
4. `deviceState === "active"` → `fresh-active`.
5. Anything else (`inactive`, missing, unknown) → `inactive`.

Tested with a small table-driven vitest in `marker-state.test.ts`.

### Live data hook
`web/src/app/sites/[siteArea]/use-live-overlay.ts` (new) —
`useQueries` fan-out, one query per **placed** device (skip the
unplaced ones; they don't render markers):

```ts
queryKey: ["overlay", siteArea, deviceId, primaryProp]
queryFn:  api.getTelemetry(deviceId, { controlledProperty: primaryProp, lastN: 1 })
refetchInterval: 30_000
refetchIntervalInBackground: false   // honors document.hidden
staleTime: 15_000
enabled: !!primaryProp
```

Returns `Map<deviceId, { value: number; unit: string|null; iso: string }>`.
Devices without a `primary_property` are absent from the map; the
marker still renders, just without a numeric badge.

### Marker component
Replace the inline `<button>` inside
`web/src/app/sites/[siteArea]/page.tsx` with a new
`web/src/app/sites/[siteArea]/live-marker.tsx`. The marker:

- Receives `Placement` + the matching live entry (or `undefined`).
- Computes `MarkerState` via `classifyMarker`.
- Wraps in `<TooltipProvider><Tooltip>` (existing shadcn primitive
  already used in the app).
- Visuals:

| state              | bg                            | border          |
|--------------------|-------------------------------|-----------------|
| fresh-active       | `bg-emerald-500 text-white`   | solid           |
| fresh-maintenance  | `bg-amber-500 text-white`     | solid           |
| inactive           | `bg-muted text-muted-foreground` | solid        |
| stale              | `bg-emerald-200/40 text-emerald-900` | dashed   |
| no-data            | `bg-muted/40 text-muted-foreground`  | dashed   |

(Stale uses the underlying state's hue at 40 % opacity + dashed
border, so a stale-active reads as "should be green but isn't
reporting".)

The numeric badge inside the pill renders
`Number.isInteger(v) ? v : v.toFixed(2)` followed by the unit (when
present). If `primary_property` is missing or last entry isn't a
finite number, render `—`.

Drag-and-drop: keep the same `draggable` / `onDragStart` /
`onDragEnd` props the current button has — `LiveMarker` accepts
them as plain props and forwards them to the root element. No
change to `onPlanDrop` logic.

### Page wiring
In `page.tsx`:
1. Read `placements.data` (already does).
2. Pass `siteArea` + `placed` into `useLiveOverlay`.
3. For each `p` in `placed`, render `<LiveMarker p={p} live={map.get(p.device_id)} ...drag>`.

The `useQueries` hook is called at component scope, so the array
length changing as new devices are placed only causes the new
queries to mount; react-query handles it correctly.

### Background-tab pause
`useQueries`' `refetchIntervalInBackground: false` already pauses
polling when the tab is hidden. No extra `visibilitychange` handler
needed.

### i18n keys (en + es)

```
sites.overlay.tooltipState        → "State"
sites.overlay.tooltipProperty     → "Property"
sites.overlay.tooltipUpdated      → "Updated"
sites.overlay.tooltipNoSamples    → "No samples yet"
sites.overlay.legend              → "Active · Maintenance · Inactive · Stale"
sites.overlay.deviceState.active        → "Active"
sites.overlay.deviceState.maintenance   → "Maintenance"
sites.overlay.deviceState.inactive      → "Inactive"
sites.overlay.deviceState.unknown       → "Unknown"
```

A small static legend strip beneath the floorplan (a row of four
coloured dots + label) so users learn the palette.

## Risks
- `useQueries` fan-out grows with site size. Mitigation: A.2 caps
  the badge at lastN=1 per device; one site is tens of devices,
  not hundreds. The follow-up `/sites/{area}/live` aggregate will
  collapse this to a single request when needed.
- `deviceState` value casing depends on Orion entity. We accept the
  exact strings `"active"` / `"maintenance"` / `"inactive"`; any
  other value classifies as `inactive`.
- Tooltip on a draggable element: shadcn `Tooltip` opens on hover
  /focus, not on click, so it doesn't conflict with HTML5 drag.
