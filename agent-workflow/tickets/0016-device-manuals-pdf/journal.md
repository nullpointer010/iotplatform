# Journal

## 2026-04-30 — kickoff

User said "Go next ticket, approve, do all recommended". Picked
`0016 device-manuals-pdf` per the roadmap (next unchecked extras).
Approved both requirements and design with the recommended defaults
listed in the requirements doc:

- Local Docker volume + Postgres metadata (no MinIO).
- 10 MiB hard cap, PDF-only (magic bytes + content-type check).
- RBAC: list/get = viewer+; upload = operator+; delete = admin only
  (mirrors `DELETE /devices/{id}`).
- New "Manuales" tab on the device detail page; click-to-open PDF.

Will report back on completion with test counts.

## 2026-04-30 — closed

Backend: 24 new tests in `test_manuals.py` (happy path + 415/413/404/401
+ full RBAC matrix). Total `make test` → 124 passed (was 100).
Web: tsc clean, vitest 5/5, `next build` 7/7 routes.

Decisions:
- Mounted the PDF storage at `/var/lib/iot/manuals` via a named Docker
  volume `iot_manuals` defined in `compose/docker-compose.base.yml`,
  attached on `iot-api` from `docker-compose.api.yml`. Compose prefixes
  the on-host name with the project, so the actual volume is
  `compose_iot_manuals`.
- Magic-byte check (`%PDF-`) on the first chunk catches files with a
  lying `Content-Type: application/pdf` header. The dedicated
  `test_upload_pdf_content_type_but_wrong_magic_415` guards that.
- Delete is `admin`-only (mirrors `DELETE /devices/{id}`); upload is
  `operator/maintenance_manager(+admin)`. Hard-coded with
  `require_roles()` (admin implicit).
- Client-side reject for non-PDF / >10 MiB files keeps the upload UX
  snappy without round-tripping bad files through the API.
