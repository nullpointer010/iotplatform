# Journal

## 2026-05-01 — kickoff

User: "All working. Go for next ticket". Picked
`0017 internal-greenhouse-map`. Approved with the recommended defaults:
- One floor-plan image per `site_area` (PNG/JPEG/WebP, 10 MiB cap).
- Placements stored as `(x_pct, y_pct)` percentages so resizing the
  image doesn't invalidate them.
- Reuse the `iot_manuals` Docker volume; floor plans live under a
  `floorplans/` subdir keyed by hash of `site_area` (ASCII-safe).
- RBAC: read = viewer+; upload + drag-place = operator+; delete = admin.

## 2026-05-01 — close

Implemented end-to-end and shipped:

- Backend: `models_floorplans.py` (`SiteFloorplan` keyed by `site_area`,
  `DevicePlacement` keyed by `device_id` UUID), alembic 0003,
  `app/floorplans.py` storage helper (magic-byte check for PNG/JPEG/
  WebP, 10 MiB cap, sha256-keyed filenames, atomic `os.replace`), and
  `routes/floorplans.py` exposing `/sites`, `PUT/GET/DELETE
  /sites/{site_area}/floorplan`, `GET /sites/{site_area}/placements`,
  and `PUT/DELETE /devices/{id}/placement`.
- Web: `/sites` index card grid, `/sites/[siteArea]` floor-plan view
  with HTML5 drag-and-drop markers in % coordinates, side tray for
  unplaced devices, upload + replace + delete (admin) controls. Top
  nav gets a "Sitios" link; i18n keys `sites.*` in es+en.
- Tests: `tests/test_floorplans.py` adds 21 tests (happy path, 415
  non-image, 413 oversize, 422 placement out of range, 404 unknown
  site/device/bad UUID, full RBAC matrix, 401 unauth). `make test`
  green at 145/145. tsc clean, vitest 5/5, next build OK.

Notes:

- Used a strict streaming-cap-then-magic check rather than reading the
  whole file twice; replaces sibling-extension files when a site
  changes format so we never accumulate stale plans.
- Placement uses `Float` 0–100; one row per device, deleted on demand
  by an admin (operators only upsert / overwrite).
- `from sqlalchemy import func as _f` then `row.updated_at = _f.now()`
  is a small ORM trick to force the timestamp column to refresh on
  upsert without adding an `onupdate=` clause that would also fire on
  unrelated UPDATEs.
