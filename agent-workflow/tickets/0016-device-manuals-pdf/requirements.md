# Ticket 0016 — device-manuals-pdf

## Problem
Operators in the field need quick access to vendor PDF manuals for the
sensors and gateways they install. Today the platform offers no way to
attach a manual to a `Device`; ops have to dig through email or shared
drives.

## Goal
Authenticated users can upload PDF manuals to a device, list them, view
them in the browser, and (with sufficient role) delete them. Storage is
local: a Docker named volume on the API container plus a Postgres
metadata table — no MinIO yet.

## User stories
- As an operator, I want to upload a PDF manual to a device so that
  anyone working on it can find the vendor docs in one click.
- As a viewer, I want to see and read the manuals attached to a device
  without being able to upload or delete them.
- As an admin, I want to delete obsolete manuals to keep the device
  page tidy.

## Acceptance criteria (verifiable)
- [ ] `POST /api/v1/devices/{id}/manuals` (multipart/form-data, field
  name `file`) stores the PDF and returns 201 with metadata.
  Rejects: 404 on unknown device, 415 if `content_type != application/pdf`,
  413 if size > 10 MiB, 422 if the field is missing.
- [ ] `GET /api/v1/devices/{id}/manuals` returns the list (200, empty
  array on no manuals; 404 on unknown device).
- [ ] `GET /api/v1/manuals/{manual_id}` streams the PDF with
  `Content-Type: application/pdf` and a `Content-Disposition` filename.
  404 on unknown id.
- [ ] `DELETE /api/v1/manuals/{manual_id}` removes both the row and the
  file on disk; 204 on success, 404 on unknown id, idempotent.
- [ ] RBAC: list+download = viewer/operator/maintenance_manager;
  upload = operator/maintenance_manager; delete = admin only
  (mirrors the device delete rule). All routes 401 unauthenticated.
- [ ] Postgres table `device_manuals(id, device_id, filename,
  content_type, size_bytes, storage_key, uploaded_at, uploaded_by)`
  via Alembic.
- [ ] Files are stored under the `iot-manuals` Docker named volume
  mounted at `/var/lib/iot/manuals/` in the API container, keyed by
  the row's UUID (one PDF per row, no original-name collision).
- [ ] UI: device detail has a new "Manuales" tab listing manuals
  (filename, size, uploaded date), with an `<input type="file">` upload
  card visible only to operator+admin; trash icon visible only to admin;
  click row → opens PDF in a new tab.
- [ ] Existing pytest suite stays green; new tests cover the 4 endpoints
  + RBAC matrix.

## Out of scope
- Object storage (MinIO/S3). Local volume only.
- Versioning of manuals (uploading the same filename twice creates two
  rows; that's fine).
- Inline PDF annotation / search inside the PDF.
- Manuals attached to entities other than `Device`.
- Quota enforcement beyond the per-file 10 MiB cap.

## Open questions
None — the recommended defaults above are taken as approved.
