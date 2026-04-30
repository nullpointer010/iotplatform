# Ticket 0012 — devices-external-map

## Problem
The web UI knows the geographic location of every device (`location.latitude`,
`location.longitude`, `location.site_area`) but never shows it on a map.
Operators must read decimal numbers like `36.8341 / -2.4021` and mentally
project them onto Almería. On the device form, coordinates are typed by hand,
which is error-prone and hides obvious mistakes (e.g. swapped lat/lng,
country-level typos).

## Goal
Add a single, lightweight Leaflet + OpenStreetMap surface to the web app that
(a) shows every geolocated device on the devices list, (b) shows the single
device's pin on its overview tab, and (c) lets the user click the map to
fill `latitude` / `longitude` in the device form. No API key, no paid tiles,
no new external service.

## User stories
- As an operator, on the devices list I want to switch to a "Map" view so I
  can see at a glance where the IFAPA / UAL devices are deployed in Almería.
- As an operator, on the device detail (overview tab) I want a small map with
  a pin so I can confirm a device is where I expect.
- As an operator, on the device create / edit form I want to click on the map
  to set latitude / longitude (or drag a pin), so I do not have to type
  decimals.
- As an operator, when a device has no location I want it to be skipped on
  the map (and the form to start centred on Almería) instead of breaking.

## Acceptance criteria (verifiable)

### Devices list — map view
- [ ] `/devices` has a `List | Map` toggle in the header. State is local to
  the page (no URL query param needed for v1).
- [ ] Map view renders a Leaflet map filling the available width, ~480 px
  tall, with OSM tiles (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`,
  attribution `© OpenStreetMap contributors`).
- [ ] One marker per device that has `location.latitude` AND
  `location.longitude` numerically present. Devices without coordinates are
  silently skipped (count shown below the map: "X de Y dispositivos
  geolocalizados").
- [ ] Initial bounds: `fitBounds()` over the geolocated set. If empty,
  centre on Almería (`36.8381, -2.4597`) at zoom 11.
- [ ] Clicking a marker opens a popup with: device name (link to detail page),
  category, protocol, site area. No bulk operations.

### Device detail — single-pin map
- [ ] Overview tab renders a small map (`~280 px` tall) below the existing
  identity / location fields, only when `location` has both numeric
  coordinates. Same OSM tiles + attribution.
- [ ] One non-draggable marker at the device's coordinates. Initial zoom
  level 15.

### Device form — click to set coordinates
- [ ] Inside the existing **Location** section of `device-form.tsx`, a map
  appears below the lat/lng inputs (~280 px tall).
- [ ] Clicking anywhere on the map writes the clicked `lat` / `lng` (rounded
  to 6 decimals) into the `latitude` and `longitude` form fields. Typing in
  the inputs moves the marker. The marker is also draggable; dragging
  updates the inputs.
- [ ] If both inputs are empty on mount, the map starts centred on Almería
  (no marker). The map appears in both `/devices/new` and
  `/devices/[id]/edit`.

### Build / quality
- [ ] No SSR errors: Leaflet imports happen client-side only (`dynamic(...,
  { ssr: false })` or equivalent). `npm run build` continues to pass.
- [ ] No new global CSS file: Leaflet's stylesheet is imported once in the
  map component (or in `app/layout.tsx` as a side-effect import) and is
  scoped via Tailwind-friendly markup.
- [ ] No tracking, no remote tile API key, no paid CDN. The only outbound
  request added is to `tile.openstreetmap.org`.
- [ ] All visible new strings (toggle labels, "Map" / "Lista", the
  geolocated-count caption) live in `messages/{es,en}.json` under a new
  `map.*` namespace.
- [ ] `npx tsc --noEmit` clean and `npx next build` green after the change.
  Existing vitest suite still passes (no new tests required for v1; map
  interactions are visual).

## Out of scope
- Heatmaps, marker clustering, custom icons per category — v1 uses Leaflet's
  default blue marker.
- Drawing polygons / polylines for `site_area` boundaries (deferred to 0017
  internal-greenhouse-map).
- Geocoding addresses to coordinates (Nominatim integration) — manual
  pin-drop only.
- Persisting the map zoom / pan in URL or cookie.
- Mobile gestures tuning beyond Leaflet's defaults.
- Updating the FastAPI backend or the `Device` schema — coordinates already
  exist as `location.latitude` / `location.longitude`.

## Open questions
1. **Toggle location.** Option A: a tab-style `List | Map` switch in the
   page header. Option B: a separate `/devices/map` route. Recommendation:
   A (no new route, reversible, matches the 0011 surgical-changes ethos).
2. **Map library.** Option A: `react-leaflet` (idiomatic React wrapper,
   ~30 kB gzipped on top of Leaflet). Option B: vanilla `leaflet` driven
   from a `useEffect`. Recommendation: A — fewer foot-guns with React
   reconciliation, well documented, MIT.
3. **Tile attribution position.** Option A: Leaflet default
   (bottom-right corner, in-map). Option B: render below the map as plain
   text. Recommendation: A — required by OSM tile usage policy, default
   covers it.
4. **Empty-state on the form.** Option A: hide the map until the user
   enters at least one coordinate or clicks. Option B: always render the
   map, centred on Almería, with no marker until the user clicks.
   Recommendation: B (lower friction, the user's current request was
   "click to fill" so the map must always be visible).
