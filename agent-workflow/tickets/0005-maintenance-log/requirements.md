# 0005 — maintenance-log

## Why

`backend.md` defines the maintenance history schema and endpoints under
`/devices/{id}/maintenance/log` and `/maintenance/operation-types`.
Auditing what was done on each device, when, by whom, is independent
from the Orion context and lives in PostgreSQL.

## What

Postgres-backed CRUD for two tables defined in `backend.md`:

- `maintenance_operation_types` (catalogue, extensible).
- `maintenance_log` (per-device audit trail).

Schema is created with **Alembic** migrations. Migrations run
automatically on API startup (the existing dev-stack control plane is
`make up`; we don't want a separate `make migrate` step for now — it's
idempotent and cheap).

## Acceptance criteria

### Operation types catalogue

1. `GET /api/v1/maintenance/operation-types` → 200 with the (initially
   empty) list.
2. `POST /api/v1/maintenance/operation-types` with
   `{name, description?, requires_component?}` → 201 with the created row
   (id auto-generated).
3. `POST` with duplicate `name` → 409.
4. `POST` with missing `name` → 422.
5. `PATCH /api/v1/maintenance/operation-types/{id}` → 200 with the
   updated row. Unknown id → 404.
6. `DELETE /api/v1/maintenance/operation-types/{id}` → 204. Unknown id →
   404. If a `maintenance_log` row references the type → 409.

### Maintenance log

7. `POST /api/v1/devices/{device_id}/maintenance/log` with valid body →
   201 with the created row.
8. `device_id` is a UUID; if no Device entity exists in Orion → 404.
9. `operation_type_id` must point to an existing operation type → 422
   (validation error: it's a request-body invariant, not a path
   identifier).
10. If the operation type has `requires_component=true` and the request
    omits `component_path` → 422.
11. `start_time` is required; `end_time` optional; if both present
    `end_time >= start_time` → otherwise 400.
12. `GET /api/v1/devices/{device_id}/maintenance/log` → 200 list,
    optional `from_date`, `to_date`, `page` (≥1), `page_size`
    (1–500, default 50). Bad pagination → 422; bad date range
    (`from > to`) → 400.
13. `PATCH /api/v1/maintenance/log/{log_id}` (e.g. set `end_time`,
    `details_notes`) → 200 with updated row. Unknown id → 404. Empty
    body → 422.
14. `DELETE /api/v1/maintenance/log/{log_id}` → 204. Unknown id → 404.
15. The full pytest suite (devices + telemetry + maintenance) is green
    via `make test`.

## Out of scope

- Authentication / RBAC. The spec calls for `maintenance_manager`,
  `admin`, `viewer`, `operator` roles; that's ticket 0009.
- `performed_by_id` validation against a `users` table — Keycloak is not
  yet integrated. The column is stored as nullable UUID; the API neither
  validates nor enriches it for now.
- Device deletion cascade — devices live in Orion. If a device is
  removed from Orion, its maintenance log rows remain (auditable
  history). Orphan-cleanup is an operational decision deferred to a
  later ticket.

## Open questions

None blocking.
