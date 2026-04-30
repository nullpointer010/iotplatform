# Tasks — Ticket 0012 (devices-external-map)

- [x] T1 Install `leaflet`, `react-leaflet`, `@types/leaflet` (dev) in
  `web/`. Verify: `grep -E '"(leaflet|react-leaflet)"' web/package.json`
  returns both, `npm install` exits 0.
- [x] T2 Create `web/src/components/map/device-map.tsx` (the only file
  that imports `react-leaflet`/`leaflet`): three modes (`list`, `single`,
  `picker`), default-icon-path fix, OSM tile layer + attribution,
  Almería fallback constant, `useMapEvents` for picker click,
  `Marker draggable` + `eventHandlers.dragend` for picker drag.
  Verify: `npx tsc --noEmit` clean.
- [x] T3 Create `web/src/components/map/device-map.client.tsx` —
  `dynamic(() => import("./device-map"), { ssr: false })` re-export,
  re-exports prop type. Verify: file exists, imports only `next/dynamic`
  (`grep -n leaflet web/src/components/map/device-map.client.tsx` →
  empty).
- [x] T4 Add `map` namespace to `web/src/i18n/messages/es.json` and
  `en.json`: `view.list`, `view.map`, `geolocated`, `single.title`,
  `picker.hint`. Verify: both JSONs parse and contain the keys.
- [x] T5 Wire devices list page: add `List | Map` toggle in
  `web/src/app/devices/page.tsx` header, conditional render
  (`<DeviceMapClient mode="list" devices={filtered} />` vs existing
  table), geolocated count caption under map. Verify: `npm run dev` →
  `/devices` shows toggle, switching to Map shows ~50 markers around
  Almería with the seed data, popup link navigates to detail.
- [x] T6 Wire device detail overview: in
  `web/src/app/devices/[id]/overview-tab.tsx`, render
  `<DeviceMapClient mode="single" lat lng />` after the location field
  block when both coords are numeric. Verify: detail page of a seeded
  device shows the small map with one pin; a device with `location =
  null` shows no map.
- [x] T7 Wire device form picker: in
  `web/src/components/forms/device-form.tsx`, inside the existing
  Location section, render `<DeviceMapClient mode="picker" lat lng
  onChange />`. Two-way bind via `form.watch` + `form.setValue`, round
  to 6 decimals, `shouldDirty: true, shouldValidate: false`. Verify:
  `/devices/new` and `/devices/[id]/edit` — clicking the map fills
  inputs; dragging the pin updates inputs; typing inputs moves the pin.
- [x] T8 Run `npx tsc --noEmit && npx next build` in `web/`. Verify:
  both exit 0, all 7 routes still build, no SSR window error.
- [x] T9 Run `npm test` (vitest) in `web/`. Verify: existing 2 tests
  still pass.
- [x] T10 Update `journal.md` with decisions (react-leaflet over vanilla,
  toggle-not-route, picker rounding) and any gotchas (default-icon
  fix, fitBounds-singleton, dynamic-import boundary).
- [x] T11 Fill `review.md` self-review section.
