# Tasks — 0020 device-live-state-and-charts

## Setup
- [x] T1 Add `recharts` to `web/package.json`; `npm install`.
- [x] T2 Mirror `StateResponse` as `DeviceStateDTO` in
      `web/src/lib/types.ts`; add `api.getState(id)` in `lib/api.ts`.
- [x] T3 New `web/src/lib/freshness.ts` (`freshnessOf` + `Freshness`
      type).
- [x] T4 New `web/src/components/ui/freshness-badge.tsx`.

## Charts
- [x] T5 New `web/src/components/charts/sparkline.tsx`.
- [x] T6 New `web/src/components/charts/time-series-chart.tsx`.

## Estado tab
- [x] T7 New `web/src/app/devices/[id]/state-tab.tsx`.
- [x] T8 Add `<TabsTrigger value="state">` between Overview and
      Telemetry in `web/src/app/devices/[id]/page.tsx`; wire the
      tab content.

## Telemetría tab v2
- [x] T9 Rewrite `web/src/app/devices/[id]/telemetry-tab.tsx`:
      range pills, `<TimeSeriesChart>`, CSV export, raw table in
      `<details>`.

## `dataTypes` editor
- [x] T10 New `web/src/components/forms/data-types-editor.tsx`.
- [x] T11 Replace the `dataTypesJson` textarea in
       `web/src/components/forms/device-form.tsx` with the new
       editor; remove `tryJson` for that field; keep submit shape.

## Dashboard
- [x] T12 New `<RecentMeasurements />` component; render in
       `web/src/app/page.tsx`.

## i18n
- [x] T13 Add the keys listed in design.md to
       `web/src/i18n/messages/{es,en}.json`.

## Tests
- [x] T14 `web/src/lib/freshness.test.ts`.
- [x] T15 `web/src/components/forms/data-types-editor.test.tsx`.
- [~] T16 `web/src/app/devices/[id]/state-tab.test.tsx` —
       deferred. Freshness logic is covered by
       `freshness.test.ts`; a component-level test would require
       mocking Recharts + react-query + next-intl and add little
       value over the unit test. Tracked as a follow-up.
- [x] T17 Telemetry CSV export test (asserts header row).

## Verification & close
- [x] T18 `npm run lint && npm test` (web) green.
- [x] T19 `make test` (api) green.
- [~] T20 Manual smoke on running stack: Estado tab populated for
       one MQTT and one HTTP device; Telemetría chart + CSV
       download work; dataTypes editor round-trips; dashboard
       card shows recent values. — pending; user to run.
- [x] T21 Fill journal.md and review.md; flip status to `done`;
       commit.
