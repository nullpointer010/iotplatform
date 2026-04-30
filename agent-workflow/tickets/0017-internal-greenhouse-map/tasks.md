# Ticket 0017 — tasks

- [x] T1  `app/models_floorplans.py`: `SiteFloorplan`, `DevicePlacement`.
- [x] T2  Alembic `0003_floorplans_and_placements.py`.
- [x] T3  `app/schemas_floorplans.py`: `SiteOut`, `PlacementOut`,
       `PlacementIn` (validators 0..100).
- [x] T4  `app/floorplans.py`: storage helpers (PNG/JPEG/WebP magic),
       `MAX_BYTES`, `save_streaming`, `delete`, `path_for`.
- [x] T5  `app/routes/floorplans.py`: 7 endpoints with `require_roles`.
- [x] T6  Wire router in `app/main.py`.
- [x] T7  `tests/conftest.py`: extend pg_clean TRUNCATE list.
- [x] T8  `tests/test_floorplans.py`: happy + edges + RBAC + 401.
- [x] T9  `web/src/lib/types.ts`: `SiteSummary`, `Placement`.
- [x] T10 `web/src/lib/api.ts`: `listSites`, `getFloorplanUrl`,
       `uploadFloorplan`, `deleteFloorplan`, `listPlacements`,
       `savePlacement`, `deletePlacement`.
- [x] T11 `web/src/app/sites/page.tsx` (index).
- [x] T12 `web/src/app/sites/[siteArea]/page.tsx` (floorplan view +
       drag).
- [x] T13 Top-nav: add "Sitios" link.
- [x] T14 i18n: `sites.*` keys in es.json + en.json.
- [x] T15 `make test` 100 % green; tsc + vitest + next build clean.
- [x] T16 Roadmap entry, journal, review, status → done; commit.
