# Journal — Ticket 0012 (devices-external-map)

## 2026-04-30
- Decision: `react-leaflet@4.2.1` (peer = react@^18) over `react-leaflet@5`
  (peer = react@^19). The web app is on react@18.3.1; pinning to v4 avoids
  `--legacy-peer-deps` and a downgrade risk in the future.
- Decision: one shared `<DeviceMap mode="list|single|picker">` component
  with a single `next/dynamic({ ssr: false })` boundary in
  `device-map.client.tsx`. Every page imports the client wrapper; nothing
  else imports `leaflet` or `react-leaflet`. This is the only safe way
  to keep `window` references out of the server bundle.
- Decision: `List | Map` toggle is component-local state (`useState`), no
  URL query and no separate route. Reversible, surgical, matches 0011 ethos.
- Decision: picker rounds to 6 decimals (`Math.round(n * 1e6) / 1e6`),
  writes through `setValue(..., { shouldDirty: true, shouldValidate: false })`
  to avoid feedback loops between drag/click and form re-render.
- Decision: `fitBounds` is unsafe with a single point (zooms to max);
  for `geo.length === 1` use `setView([...], 13)` instead.
- Surprise: `delete (L.Icon.Default.prototype as any)._getIconUrl` triggers
  Next's lint rule `@typescript-eslint/no-explicit-any` even when prefixed
  with `eslint-disable-next-line` (the rule definition is missing in the
  Next eslint preset). Fixed by typing the prototype as
  `{ _getIconUrl?: unknown }`.
- Surprise: Leaflet image imports (`marker-icon.png`) come back as a
  webpack `StaticImageData` object in Next; the runtime `.src` extraction
  has to handle both shapes for safety.

## Lessons (to propagate on close)
- → `memory/patterns.md`: For any client-only browser-API library
  (Leaflet, charting libs, Quill, etc.) in Next App Router, isolate the
  import in a `*.client.tsx` re-exporting `dynamic(() => import(...),
  { ssr: false })`. Keep its own CSS import inside the dynamic module.
- → `memory/gotchas.md`: `react-leaflet@5` requires React 19 — pin to
  `^4.2.1` while the app is on React 18.
- → `memory/gotchas.md`: `Map.fitBounds` with one LatLng point zooms to
  the deepest zoom level; branch on `length === 1` and use `setView`.
- → `memory/gotchas.md`: Next's lint preset does not ship the
  `@typescript-eslint/no-explicit-any` *rule definition*, so disable
  comments fail. Use a precise type instead of `any`.
