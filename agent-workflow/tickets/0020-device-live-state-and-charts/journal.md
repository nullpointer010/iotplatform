# Journal — Ticket 0020

## 2026-05-05 — Plan & implementation
Three UI deliverables on the existing `/state` and `/telemetry`
endpoints. No backend changes.

### Decisions
- **Recharts** as the chart library. Single new dep, ~80 kB gz.
  Tree-shaken via top-level imports, so production bundle should
  be acceptable for the seed fleet.
- **Polling** (15 s for `/state`, 60 s for sparkline,
  30 s for the dashboard card) instead of streaming. Matches the
  simulator cadence (10 s) without introducing SSE/WS.
- **Client-side CSV** export. The endpoint already caps lastN at
  1000, so a `Blob` download is enough.
- The `dataTypes` editor stores its value as the same JSON string
  the form already round-trips. Schema (`zod`) and submit shape
  (`toApiPayload`) untouched. The textarea was dropped, but the
  `dataTypesJson` form field stays.

### Surprises
- Recharts' `Tooltip.formatter` types in v3 broaden `value` to
  `ValueType | undefined`; coerce to string in the formatter to
  appease tsc.
- next-intl strict-types reject `t(\`telemetry.range.${r}\` as const)`
  on a non-literal template; replaced with a small `rangeLabel`
  switch.
- The `dashboard` key was already present in `messages/*.json`;
  the new `recentTitle` / `recentEmpty` keys were merged into the
  existing block to avoid duplicate JSON keys.

### Files touched
- new `web/src/lib/freshness.ts` + test
- new `web/src/components/ui/freshness-badge.tsx`
- new `web/src/components/charts/{sparkline,time-series-chart}.tsx`
- new `web/src/components/forms/data-types-editor.tsx` + test
- new `web/src/components/dashboard/recent-measurements.tsx`
- new `web/src/app/devices/[id]/state-tab.tsx`
- rewritten `web/src/app/devices/[id]/telemetry-tab.tsx` + test
- `web/src/app/devices/[id]/page.tsx` (Estado tab wiring)
- `web/src/app/page.tsx` (Recent measurements card)
- `web/src/components/forms/device-form.tsx` (dataTypes editor)
- `web/src/lib/{api.ts,types.ts}` (`getState` + DTO)
- `web/src/i18n/messages/{en,es}.json`
- `web/package.json` (recharts ^3.8)

### Verified
- `npx tsc --noEmit`: clean.
- `npm run lint`: clean.
- `npm test` (web): 17 passed.
- `make test` (api): 183 passed.

## 2026-05-05 — Post-merge fixes

User-driven smoke (T20) revealed three issues; all fixed in the
same ticket since they were direct regressions of A.4–A.5 and A.2:

1. **24h/7d/30d stuck on "Cargando…"**: `rangeWindow` was called
   inline in the render body, so `Date.now()` produced a new
   `fromDate`/`toDate` on every render, mutating the
   react-query `queryKey` and triggering an infinite refetch.
   Wrapped in `useMemo([range, customFrom, customTo])`.
2. **Raw table showed UTC while chart showed local** (and used
   12h AM/PM via `toLocaleString()`): switched the table cell to
   date-fns `yyyy-MM-dd HH:mm:ss` (24h, local). Original UTC ISO
   preserved in the cell `title` tooltip. Sorted descending so
   newest is on top, matching the chart's right edge.
3. **CSV column drift**: kept the canonical `dateObserved` ISO and
   added a `localTime` column (`yyyy-MM-dd HH:mm:ss`) so the
   spreadsheet view matches the on-screen chart. New header:
   `dateObserved,localTime,numValue,unitCode`. Test updated.

Latent bug found during the audit and fixed:
- `state-tab.tsx::unitOf` looked up
  `device.dataTypes[attr].unitCode`, but `DataTypesEditor`
  serialises plain strings (`"Number"` / `"Text"`); the property
  branch was dead and the unit never appeared on Estado cards.
  Removed `unitOf` and pulled `unitCode` from the sparkline's
  telemetry response (`entries[0].unitCode`), which is the same
  source the chart uses.

Verified again: `tsc --noEmit` clean, `npm run lint` clean,
`npm test` 17/17.
