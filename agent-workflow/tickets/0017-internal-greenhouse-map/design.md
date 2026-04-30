# Ticket 0017 — design

## Storage

Reuse the `iot_manuals` named Docker volume mounted at
`/var/lib/iot/manuals`. Floor plans live in a sibling subdir:
`/var/lib/iot/manuals/floorplans/`. New helper `app/floorplans.py`
(modelled on `app/manuals.py`):

- Storage key = `sha256(site_area)[:32].<ext>` so disk paths are
  ASCII-safe regardless of user input (`Invernadero 1`, `La Cañada`,
  …) and stable across uploads (so replacing a plan reuses the same
  file slot — atomic `os.replace()`).
- 10 MiB cap, magic-byte check for PNG / JPEG / WebP signatures.
- `save_streaming(site_area, ext, upload)` / `delete(site_area, ext)`
  / `path_for(site_area, ext)`.

## Postgres tables

Alembic `0003_floorplans_and_placements`:

```sql
site_floorplans
  site_area     varchar(255) PRIMARY KEY
  filename      varchar(255) NOT NULL
  content_type  varchar(100) NOT NULL
  size_bytes    bigint       NOT NULL
  storage_key   varchar(80)  NOT NULL
  uploaded_at   timestamptz  NOT NULL default now()
  uploaded_by   varchar(255) NULL

device_placements
  device_id   uuid PRIMARY KEY
  x_pct       double precision NOT NULL  -- 0..100
  y_pct       double precision NOT NULL  -- 0..100
  updated_at  timestamptz NOT NULL default now()
  updated_by  varchar(255) NULL
```

`site_area` as the PK is fine: it's a free-text column on the device
in Orion already. Renaming a site requires re-uploading the plan and
re-placing devices — out of scope.

## API

| Route                                            | Method | Roles                                | Notes                              |
| ------------------------------------------------ | ------ | ------------------------------------ | ---------------------------------- |
| `/sites`                                         | GET    | viewer, operator, mgr                | distinct site_area + counts        |
| `/sites/{site_area}/floorplan`                   | PUT    | operator, mgr                        | multipart, 201 first / 200 replace |
| `/sites/{site_area}/floorplan`                   | GET    | viewer, operator, mgr                | streams image                      |
| `/sites/{site_area}/floorplan`                   | DELETE | admin only                           | 204 / 404                          |
| `/sites/{site_area}/placements`                  | GET    | viewer, operator, mgr                | merge devices ∪ placements         |
| `/devices/{device_id}/placement`                 | PUT    | operator, mgr                        | JSON {x_pct, y_pct}                |
| `/devices/{device_id}/placement`                 | DELETE | admin only                           | 204 / 404                          |

`{site_area}` is path-param-encoded; FastAPI URL-decodes for us. We
don't validate it against Orion (there is no canonical list); the
`/sites` index returns whatever currently exists in
`device.location.site_area`.

For `/sites`, query Orion `GET /v2/entities?type=Device&attrs=location`
and count distinct `site_area` values, then LEFT JOIN with
`site_floorplans` to set `has_floorplan: bool`.

For `/sites/{site_area}/placements`, fetch devices with
`q=location.site_area==<value>` from Orion, LEFT JOIN
`device_placements` so devices without a placement still come back.

## Web

- New page `web/src/app/sites/page.tsx` (already a sibling of
  `/devices`). Lists site_areas as cards: device count, plan badge.
  Click → `/sites/[siteArea]`.
- New page `web/src/app/sites/[siteArea]/page.tsx`:
  - Header: site name, "Subir plano" upload button (operator+).
  - If no plan: empty-state with upload prompt; otherwise:
  - `<img>` of the floor plan + absolutely-positioned markers via
    Tailwind. Markers use `pointer-events-auto` and are draggable
    by mouse + touch (HTML5 drag-and-drop API). Coordinates are
    `% of natural image size` → naturally responsive.
  - Right-side tray of unplaced devices (drag onto plan).
  - On drop, fire `api.savePlacement(device_id, {x_pct, y_pct})`
    with optimistic update + rollback on error.
- Top-nav: add "Sitios" item between Devices and Maintenance.
- i18n keys under `sites.*`.

## Tests

- `tests/test_floorplans.py`:
  - happy round-trip put/get/delete floor-plan (admin).
  - 415 for non-image, 413 for oversize, 404 for unknown site
    floor-plan.
  - placement put: ok (operator); 422 on x=-1, x=101, missing field;
    404 on unknown device.
  - placement get list: returns devices with x/y null when no row.
  - RBAC matrix on each route + 401 unauth.
- conftest `pg_clean` adds `site_floorplans, device_placements` to
  the TRUNCATE list.

## Out-of-scope reminders

- The drop target is the `<img>` element. We do **not** persist the
  natural image size in the DB; the browser already has it via
  `naturalWidth/Height`. Storing percentages keeps coordinates valid
  even if the image is replaced with one of a different size.
- No drag handle, no z-order, no marker grouping. Plain dots.
