# Design — Ticket 0012 (devices-external-map)

## Approach

Add Leaflet + `react-leaflet` to the web app and ship one shared
client-only `<DeviceMap>` component plus three thin call sites:

- `web/src/components/map/device-map.tsx` — the only file that imports
  `react-leaflet` / `leaflet`. Three render modes via a discriminated
  `mode` prop: `"list"` (many markers + popups), `"single"` (one fixed
  marker, read-only), `"picker"` (one draggable marker + click-to-set,
  emits `onChange({lat, lng})`).
- `web/src/components/map/device-map.client.tsx` — `dynamic(() => import(
  "./device-map"), { ssr: false })` re-export. **Only this file is imported
  by pages**, so Leaflet never reaches the server bundle.
- Three call sites:
  - `web/src/app/devices/page.tsx` — header gets a `List | Map` segmented
    toggle (component-local `useState`, default `list`). When `mode ===
    "map"`, render `<DeviceMapClient mode="list" devices={filtered} />`
    instead of the table. The existing search/category/protocol/state
    filters keep applying — the map only sees `filtered`.
  - `web/src/app/devices/[id]/overview-tab.tsx` — when `device.location`
    has both numeric `latitude` and `longitude`, render
    `<DeviceMapClient mode="single" lat={...} lng={...} />` after the
    location field block.
  - `web/src/components/forms/device-form.tsx` — inside the existing
    Location `<Section>`, below the `latitude`/`longitude`/`siteArea`
    inputs, render `<DeviceMapClient mode="picker" lat={form.watch(
    "latitude")} lng={form.watch("longitude")} onChange={(lat,lng) =>
    form.setValue(...)} />`. Two-way bind: typing in the inputs moves the
    pin; clicking/dragging the pin writes back through `setValue`. Round
    to 6 decimals on write.

Leaflet's CSS is imported once at the top of `device-map.tsx`
(`import "leaflet/dist/leaflet.css";`). The default-marker icon-path
glitch (Leaflet 1.x quirk under bundlers) is fixed inline by overriding
`L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl })`
with `leaflet/dist/images/*` URLs imported as static assets — kept in
`device-map.tsx` so the workaround is in one place.

For the list-view popup, render with plain JSX (Next `<Link>` works
inside `<Popup>` since react-leaflet renders into a portal). Show
`name`, `category`, `supportedProtocol`, `location.site_area`.

Almería fallback centre = `{ lat: 36.8381, lng: -2.4597 }` at zoom 11
(list/picker) or 15 (single). Defined as a constant in `device-map.tsx`.

i18n: a new `map` namespace in both catalogs:
`{ list, map, geolocated: "{n} de {total} dispositivos geolocalizados" }`.

## Alternatives considered

- **A) `react-leaflet`** — chosen: idiomatic React wrapper, MIT,
  lifecycle handled, `MapContainer`/`Marker`/`Popup`/`useMapEvents` cover
  every requirement.
- **B) Vanilla `leaflet` in a `useEffect`** — rejected: every call site
  would have to reimplement init/teardown, marker diffing, and React
  ref plumbing. More foot-guns for marginal bundle savings.
- **C) Mapbox / Google Maps** — rejected: requires API key + paid tier
  past quota; OSM + Leaflet is exactly what AC asks for.
- **D) Separate `/devices/map` route** — rejected: doubles header /
  filter scaffolding for no UX gain. The toggle is component-local.

## Affected files / new files

**New**
- `web/src/components/map/device-map.tsx` — the actual Leaflet component
  (3 modes, default-icon fix, OSM tile layer, attribution).
- `web/src/components/map/device-map.client.tsx` — `next/dynamic`
  wrapper with `ssr: false`. Re-exports the prop type.

**Modified**
- `web/package.json` + `package-lock.json` — add `leaflet`,
  `react-leaflet`, `@types/leaflet` (devDep).
- `web/src/app/devices/page.tsx` — `List | Map` toggle, conditional
  render, geolocated count under map.
- `web/src/app/devices/[id]/overview-tab.tsx` — single-pin map after
  location fields when coords present.
- `web/src/components/forms/device-form.tsx` — picker map inside the
  Location section; lat/lng inputs gain `valueAsNumber` parsing if
  needed for two-way binding.
- `web/src/i18n/messages/es.json` + `en.json` — new `map.*` keys
  (`view.list`, `view.map`, `geolocated`, `picker.hint`).

## Data model / API contract changes

None. The frontend already receives `location.latitude`,
`location.longitude`, `location.site_area` from `GET /api/v1/devices`
(see `web/src/lib/types.ts`).

## Risks

- **SSR import of `leaflet`** crashes Next during build (uses `window`).
  → Single dynamic-import boundary in `device-map.client.tsx` with
  `ssr: false`. No other file imports `leaflet` directly.
- **Default marker icons 404** in production bundles.
  → Override `L.Icon.Default` once at module scope with imported asset
  URLs from `leaflet/dist/images/*` (Webpack resolves them).
- **Picker map fights the form**: `setValue` from drag triggers a
  re-render that resets the marker position and loops.
  → Marker `position` is derived from `form.watch("latitude/longitude")`;
  drag handler writes `setValue` with `{ shouldDirty: true,
  shouldValidate: false }` and rounds to 6 decimals. Equality on the
  rounded values short-circuits the loop.
- **`fitBounds` on a single point** zooms in to max.
  → If `geolocated.length === 1`, use `setView([lat,lng], 13)` instead.
  If `0`, centre on Almería.
- **OSM tile usage policy** requires attribution + non-abusive load.
  → Leaflet's default attribution control covers it; we only have ~50
  devices in seed data so tile load is tiny.

## Test strategy for this ticket

- **Unit**: none added. Map interactions are visual; existing vitest
  suite (orion-chars) keeps running unchanged.
- **Build**: `npx tsc --noEmit` + `npx next build` must stay green.
  These catch the SSR import regression specifically.
- **Manual verification**:
  1. `make seed && cd web && npm run dev`.
  2. `/devices` — switch to Map, verify ~50 markers around Almería,
     popup shows name + category + protocol + site area, name link
     navigates to detail.
  3. `/devices/<id>` — overview tab shows a small map with one pin at
     the device's coords; devices without location show no map.
  4. `/devices/new` — pick category=sensor, protocol=http; click
     somewhere on the map; verify lat/lng fields update; drag pin;
     verify update; type new lat/lng manually; verify pin moves.
  5. `/devices/<id>/edit` — same picker behaviour, marker starts at
     current coords.
  6. Switch language EN ↔ ES via user menu — toggle and caption strings
     translate; tile attribution stays the OSM default (English, by
     OSM convention — fine).
