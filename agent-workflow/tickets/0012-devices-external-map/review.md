# Review — Ticket 0012 (devices-external-map)

## Self-review (agent)

### What changed
- New `web/src/components/map/device-map.tsx` — single Leaflet component
  with three modes: `list` (markers + popups + auto fitBounds), `single`
  (one fixed marker), `picker` (click-to-set + draggable marker). OSM
  tiles, default-marker icon-path fix, Almería fallback constant.
- New `web/src/components/map/device-map.client.tsx` — the
  `next/dynamic({ ssr: false })` boundary; the only file other code
  imports.
- `web/src/app/devices/page.tsx` — `List | Map` toggle in the header,
  conditional render of `<DeviceMap mode="list" devices={filtered} />`,
  geolocated count caption.
- `web/src/app/devices/[id]/overview-tab.tsx` — single-pin map below the
  identity/location cards when both coordinates are numeric.
- `web/src/components/forms/device-form.tsx` — `LocationPicker`
  sub-component inside the existing Location section; two-way bound to
  `latitude` / `longitude` via `form.watch` + `setValue` (rounded to 6 dp).
- `web/src/i18n/messages/{es,en}.json` — new `map.*` namespace
  (`view.list`, `view.map`, `geolocated`, `picker.hint`).
- Deps: `leaflet@^1.9.4`, `react-leaflet@^4.2.1`, `@types/leaflet@^1.9.12`.

### Why these changes meet the acceptance criteria
- AC list-toggle, list-markers, list-bounds, list-popup → `<ListMap>` in
  `device-map.tsx`; toggle in `devices/page.tsx`; `FitToDevices` handles
  bounds (singleton via `setView`, fallback Almería).
- AC geolocated-count → `t("map.geolocated", { n, total })` under map view.
- AC detail-pin → `<SingleMap>` rendered conditionally on numeric coords.
- AC picker click + drag + typing → `useMapEvents.click`, `Marker
  draggable + dragend`, and `useEffect` panTo on external value change.
- AC empty form starts on Almería → `PickerMap` falls back to ALMERIA
  when no coords.
- AC SSR → only `device-map.client.tsx` is imported by pages; it uses
  `next/dynamic` with `ssr: false`. `next build` is green.
- AC no key / no paid tiles → tile URL is
  `https://tile.openstreetmap.org/{z}/{x}/{y}.png` with the OSM
  attribution string.
- AC i18n → all visible new strings live under `map.*` in both catalogs.
- AC build/tests → `npx tsc --noEmit` clean; `npx next build` 7/7 routes;
  `npm test` 2/2 vitest.

### Known limitations / debt introduced
- Tile attribution stays in English ("OpenStreetMap contributors") even
  in `es` mode — that is OSM's canonical wording and acceptable per the
  open-question recommendation, but a follow-up could swap to a Spanish
  label while keeping the link.
- No marker clustering. Fine at 50 devices; if seed grows past a few
  hundred we should add `react-leaflet-cluster` or equivalent.
- Picker has no "use my location" button. Out of scope for v1.
- Leaflet's static images are bundled via the `leaflet/dist/images/*`
  imports; if Next's image pipeline ever drops PNG passthrough we will
  need a workaround. Currently green.

### Suggested follow-up tickets
- Cluster markers when `geolocated.length > 200` (defer until needed).
- Geocoding via Nominatim (free, no key) for the Address fields.
- Leaflet attribution in the active locale.
- Internal greenhouse map (already tracked as 0017).

## External review

<paste here output from Codex, another model, or a human reviewer>

## Resolution

- [ ] All review comments addressed or filed as new tickets
- [ ] Lessons propagated to `agent-workflow/memory/`
