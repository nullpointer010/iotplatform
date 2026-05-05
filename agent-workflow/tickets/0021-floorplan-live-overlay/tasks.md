# Tasks — 0021 floorplan-live-overlay

## Backend
- [x] T1 Extend `PlacementOut` (schemas_floorplans.py) with
      `device_state` and `primary_property` (both Optional).
- [x] T2 Add `_device_state_of` and `_primary_property_of` helpers in
      `routes/floorplans.py`; pass through `list_placements` and
      `upsert_placement`.
- [x] T3 Add `test_placements_include_state_and_primary_property` in
      `tests/test_floorplans.py`.

## Frontend
- [x] T4 Extend `Placement` in `lib/types.ts`.
- [x] T5 New `lib/marker-state.ts` (`classifyMarker` + `MarkerState`).
- [x] T6 New `lib/marker-state.test.ts`.
- [x] T7 New `app/sites/[siteArea]/use-live-overlay.ts` (useQueries
      fan-out, 30s, no background refetch).
- [x] T8 New `app/sites/[siteArea]/live-marker.tsx` (palette,
      tooltip, drag handlers).
- [x] T9 Wire `<LiveMarker>` into `app/sites/[siteArea]/page.tsx`;
      add legend strip below the floorplan.
- [x] T10 i18n keys in `messages/{en,es}.json` (`sites.overlay.*`).

## Verify & close
- [x] T11 `make test` (api) green (184 passed).
- [x] T12 `npm run lint && npm test` (web) green (23 passed).
- [~] T13 Manual smoke — pending; user to run.
- [x] T14 journal.md + review.md, flip status to done, update
      roadmap, commit.
