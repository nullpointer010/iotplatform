# Journal — 0005

## Decisions

- **`device_id` is not a real FK in Postgres.** Devices live in Orion; there is no `devices` table to reference. Existence is verified at `POST` time only. List/PATCH/DELETE never re-validate the device, so the audit trail survives Orion-side deletions — which is what "audit log" actually means.
- **`requires_component` is enforced at create time, not as a CHECK constraint.** The flag lives on the operation type, not the log row, so it cannot be expressed as a row-local CHECK. We fetch the type and validate in the route.
- **`ON DELETE RESTRICT` on `operation_type_id`.** Deleting a referenced operation type returns 409, matching the AC. Cascade would silently delete history.
- **Alembic in lifespan, not a separate `make migrate` step.** Single API replica, single dev stack. Idempotent. For multi-replica deployment this should move to an init container.
- **psycopg sync driver in tests.** TRUNCATE between tests via a session-less fixture is the simplest path; bringing in pytest-asyncio just for cleanup wasn't worth it.
- **Authentication deferred to ticket 0009.** Spec calls for `maintenance_manager`/`admin`/etc; we do not gate the routes today. The interface is finalised; the gate is bolted on later.
- **`performed_by_id` is a free-form UUID for now.** Will be wired to Keycloak `sub` claims in 0009.

## Issues hit

1. **`psycopg==3.2.3` failed to import in the container** because no libpq + no binary wheel was installed. Switched to `psycopg[binary]==3.2.3`.
2. **`detail=` payloads from FastAPI on 422 require Pydantic field-level validation, not custom `model_validator` raises mapped to 400** — ensured `model_validator` raises `ValueError`, which FastAPI maps to 422 (matches the AC for empty PATCH body and tightens the contract).

## Numbers

- 55 tests across the whole suite (19 devices + 11 telemetry/state + 25 maintenance), 4.14s wall.
