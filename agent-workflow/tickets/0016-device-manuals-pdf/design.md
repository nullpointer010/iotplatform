# Ticket 0016 — design

## Storage layout

- Docker named volume `iot-manuals`, mounted at `/var/lib/iot/manuals/`
  in the `iot-api` container. Survives container rebuilds, lives next
  to the postgres+keycloak data volumes.
- Each file stored as `<manual_uuid>.pdf` under that path. The original
  filename is kept only in the DB row. This keeps disk paths immune to
  weird user-supplied filenames (path traversal, unicode collisions).

## Postgres table

```
device_manuals
  id            uuid    PK   default uuid4
  device_id     uuid    NOT NULL                      (Orion URN tail, like maintenance_log)
  filename      varchar(255)  NOT NULL                (original, for display + download)
  content_type  varchar(100)  NOT NULL                (always "application/pdf" for now)
  size_bytes    bigint        NOT NULL
  storage_key   varchar(64)   NOT NULL                ("<manual_uuid>.pdf"; redundant with id but keeps the API self-describing)
  uploaded_at   timestamptz   NOT NULL  default now()
  uploaded_by   varchar(255)  NULL                    (Principal.username; null for backfill)

  index on device_id
```

No FK to `devices` (devices live in Orion, not Postgres — same pattern
as `maintenance_log`).

## API surface

All under `/api/v1`. JSON shape:

```
{ "id": uuid, "device_id": uuid, "filename": "vendor.pdf",
  "content_type": "application/pdf", "size_bytes": 31415,
  "uploaded_at": "...Z", "uploaded_by": "operator" }
```

| Route                                          | Method | Roles                                     | Notes                                                      |
| ---------------------------------------------- | ------ | ----------------------------------------- | ---------------------------------------------------------- |
| `/devices/{device_id}/manuals`                 | POST   | operator, maintenance_manager (+admin)    | multipart `file`; 415 non-pdf, 413 > 10 MiB                |
| `/devices/{device_id}/manuals`                 | GET    | viewer, operator, maintenance_manager     | list, ordered uploaded_at desc                             |
| `/manuals/{manual_id}`                         | GET    | viewer, operator, maintenance_manager     | stream PDF with `Content-Disposition: inline; filename=…` |
| `/manuals/{manual_id}`                         | DELETE | admin only                                | unlink file, delete row, 204                               |

Delete is admin-only to mirror `DELETE /devices/{id}` (only admin can
remove things). Upload is operator+ to match maintenance log create.

## File handling

- New helper `app/manuals.py` with `MANUALS_DIR = Path("/var/lib/iot/manuals")`
  and `save(file_id, stream)` / `delete(file_id)` / `path(file_id)`.
- `MANUALS_DIR.mkdir(parents=True, exist_ok=True)` at import time.
- Upload uses `UploadFile`; we read in 1 MiB chunks, write to a
  temporary `<id>.pdf.part` file and `os.replace()` on success. If size
  cap hit mid-stream, abort + unlink the partial.
- The 10 MiB cap is enforced by counting bytes during streaming
  (`Content-Length` is unreliable behind oauth2-proxy).
- Magic-byte check: first 5 bytes must be `%PDF-`. If not, 415.

## Ingress (oauth2-proxy)

Multipart uploads pass through unchanged because `OAUTH2_PROXY_UPSTREAMS`
already maps `/api/` to the API. No new env vars needed.

## Web

- `web/src/lib/types.ts`: `DeviceManual` interface.
- `web/src/lib/api.ts`: `listManuals`, `uploadManual` (FormData),
  `deleteManual`, `manualUrl(id)` returning the same-origin URL.
- New component `web/src/app/devices/[id]/manuals-tab.tsx` modelled on
  `maintenance-tab.tsx`:
  - Upload card (file input + submit, accept=`application/pdf`,
    client-side reject if > 10 MiB) wrapped in `<Gate roles={["operator"]}>`.
  - Table: filename (link, opens `manualUrl(id)` in new tab), size,
    uploaded date, uploaded_by, trash icon `<Gate roles={[]}>` (admin).
  - Empty state.
- `web/src/app/devices/[id]/page.tsx`: add a `<TabsTrigger value="manuals">`
  + `<TabsContent>`.
- i18n keys under `manuals.*` in `es.json` / `en.json`.

## Tests (backend)

- `tests/test_manuals.py`:
  - `test_upload_then_list_then_get_then_delete` (admin) — happy path round-trip.
  - `test_upload_non_pdf_415`.
  - `test_upload_too_big_413` (build a 10 MiB + 1 byte fake PDF).
  - `test_upload_unknown_device_404`.
  - `test_get_unknown_404` and `test_delete_unknown_404`.
  - RBAC: parametrise across viewer/operator/manager/admin, assert
    upload allowed only for operator/manager/admin, delete only for admin,
    list/get for everyone.
  - `test_unauth_*_returns_401` on each route.

Existing 100/100 tests must stay green.

## Tests (web)

- vitest sanity: `manualUrl` returns `/api/v1/manuals/<id>`. No
  end-to-end browser tests in this ticket.

## Out-of-scope reminders

- No virus scanning. Local dev only.
- No range requests / partial download. The browser PDF viewer fetches
  the whole file, which is fine at 10 MiB.
