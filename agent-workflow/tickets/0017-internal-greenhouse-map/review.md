# Review

## Self-review (2026-05-01)

**Scope adhered to.** Only routes, models, schemas, and pages explicitly
listed in `design.md` were touched; nothing in maintenance, manuals, or
device CRUD changed.

**Acceptance criteria.**

1. ✅ `GET /sites` returns one row per `site_area` with device count
   and `has_floorplan`. Devices without `site_area` are excluded.
2. ✅ `PUT /sites/{site_area}/floorplan` validates magic bytes (PNG /
   JPEG / WebP) and the 10 MiB cap (415 / 413). Replace is idempotent.
3. ✅ `GET /sites/{site_area}/floorplan` streams the file with the
   correct `content_type` and `Content-Disposition: inline`.
4. ✅ `DELETE` is admin-only via `require_roles()`.
5. ✅ `GET /sites/{site_area}/placements` lists every device whose
   `location.site_area` matches, including unplaced devices with
   `x_pct=null, y_pct=null`.
6. ✅ `PUT /devices/{id}/placement` enforces `0 ≤ x_pct, y_pct ≤ 100`
   (422 on out-of-range), 404 on unknown / malformed device id.
7. ✅ Web: site index, floor-plan page with drag-and-drop markers,
   replace / delete controls gated by RBAC, top-nav link, i18n.

**Tests.** `pytest` 145/145 green (added 21 new). `vitest` 5/5. `tsc
--noEmit` clean. `next build` clean.

**Security.** Magic-byte check rejects spoofed content-types. Storage
key is `sha256(site_area)[:32].<ext>` — user-controlled `site_area`
never appears on disk. Streaming cap blocks size-bomb uploads.

## External review

(empty — pending)
