# Ticket 0017 — internal-greenhouse-map

## Problem
The platform locates devices on a city-scale map (Leaflet, 0012), but
operators inside a single greenhouse / nave / warehouse need a
zoomed-in *internal* view: a floor-plan image of the building with the
devices placed on it. Today there is no way to upload such a plan and
no way to record the (x,y) of a device inside its `site_area`.

## Goal
For every distinct `site_area`, a manager can upload one floor-plan
image; operators can drag-place devices on it; everyone can see the
plan with markers and click a marker to jump to the device detail.

## User stories
- As a manager, I want to upload a floor-plan PNG/JPEG/WebP for an
  IFAPA greenhouse so the team has a shared visual reference.
- As an operator, I want to drag a device marker onto the spot where
  I physically installed it, so the next time someone needs to find
  the sensor they can just open the plan.
- As a viewer, I want to open the floor plan, see the markers, hover
  to see the device name, and click to open the device detail page.

## Acceptance criteria (verifiable)
- [ ] `PUT /api/v1/sites/{site_area}/floorplan` (multipart `file`)
  uploads or replaces the floor plan. Accepts `image/png`,
  `image/jpeg`, `image/webp`. 415 otherwise. 413 on > 10 MiB. 201
  on first upload, 200 on replace.
- [ ] `GET /api/v1/sites/{site_area}/floorplan` streams the image
  (200) or returns 404 if none uploaded.
- [ ] `DELETE /api/v1/sites/{site_area}/floorplan` removes row + file
  (admin only). 204 / 404.
- [ ] `GET /api/v1/sites/{site_area}/placements` returns
  `[ { device_id, name, x_pct, y_pct } ]` for every device whose
  `location.site_area` equals `site_area`. Devices without a stored
  placement still appear with `x_pct: null, y_pct: null` so the UI
  knows what to draw in the "unplaced" tray.
- [ ] `PUT /api/v1/devices/{device_id}/placement` (JSON
  `{x_pct, y_pct}`, both `0..100` floats) upserts the placement.
  422 on out-of-range. 404 on unknown device.
- [ ] `DELETE /api/v1/devices/{device_id}/placement` clears the
  placement row (204 / 404).
- [ ] RBAC: list/get = viewer+; upload+placement = operator/manager+;
  delete (floorplan or placement) = admin only.
- [ ] Postgres tables:
    - `site_floorplans(site_area pk, filename, content_type,
      size_bytes, storage_key, uploaded_at, uploaded_by)`
    - `device_placements(device_id pk, x_pct, y_pct, updated_at,
      updated_by)`
- [ ] Floor-plan files stored under the existing `iot_manuals` volume
  in a `floorplans/` subdirectory, keyed by a hash of `site_area`
  (storage filename never echoes user-supplied text).
- [ ] UI:
    - `/sites` index: list of distinct `site_area`s found in devices
      (count of devices per site, "has plan" indicator).
    - `/sites/[siteArea]` page: floor-plan image with absolutely
      positioned markers. Drag-to-place visible to operator+.
      Unplaced devices appear in a side tray; drop on the plan to
      place. Click marker → opens device detail.
- [ ] Backend pytest suite stays green; new tests cover the 6
  endpoints and RBAC.

## Out of scope
- AI-generated floor plans (the roadmap note explicitly defers this).
- Multi-floor / multi-image per site.
- Server-side image resize, thumbnail generation, watermarking.
- Real-time multi-user drag (last-write-wins is fine).
- Search/filter inside the floor-plan view.

## Open questions
None — recommended defaults (single image per site, PNG/JPEG/WebP,
10 MiB cap, percentage coordinates so resize doesn't break placement)
are taken as approved.
