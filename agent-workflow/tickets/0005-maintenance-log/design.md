# Design — 0005 maintenance-log

## Layout

```
platform/api/
  alembic.ini                 # NEW
  alembic/                    # NEW migrations dir
    env.py
    script.py.mako
    versions/
      0001_initial_maintenance.py
  app/
    config.py                 # +database_url
    db.py                     # NEW: async engine + sessionmaker
    models_maintenance.py     # NEW: SQLAlchemy 2.0 models
    schemas_maintenance.py    # NEW: Pydantic v2 models
    deps.py                   # +SessionDep
    routes/
      maintenance.py          # NEW: all 8 endpoints
    main.py                   # run alembic upgrade in lifespan; include router
  requirements.txt            # +SQLAlchemy, asyncpg, alembic, greenlet
  Dockerfile                  # COPY alembic + alembic.ini
  tests/
    test_maintenance.py       # NEW
    conftest.py               # +pg_clean fixture
platform/compose/docker-compose.api.yml  # +DATABASE_URL env, depends_on postgres
platform/.env.example         # +DATABASE_URL
```

## Persistence

PostgreSQL (already in the base stack). Schema:

| Table                          | Notes                                         |
|--------------------------------|-----------------------------------------------|
| `maintenance_operation_types`  | id UUID PK, name UNIQUE NOT NULL, description TEXT, requires_component BOOLEAN NOT NULL DEFAULT FALSE |
| `maintenance_log`              | id UUID PK, device_id UUID NOT NULL, operation_type_id UUID NOT NULL FK→operation_types(id) ON DELETE RESTRICT, performed_by_id UUID NULL, start_time TIMESTAMPTZ NOT NULL, end_time TIMESTAMPTZ NULL, component_path VARCHAR(255) NULL, details_notes TEXT NULL |

Indexes: `idx_maintenance_log_device_id`, `idx_maintenance_log_operation_type`, `idx_maintenance_log_start_time` (matches `backend.md`).

Notes:

- `device_id` is **not** a foreign key. Devices live in Orion. We
  validate device existence by calling Orion on `POST` only. List/PATCH/
  DELETE never re-validate the device — the audit log is authoritative
  even if the Orion entity is later deleted.
- `TIMESTAMPTZ` (not `TIMESTAMP`) so we never serialise a naive datetime
  back to clients.
- `ON DELETE RESTRICT` on `operation_type_id` → AC 6 (409 if referenced).

## SQLAlchemy / driver

- `SQLAlchemy[asyncio]==2.0.36`
- `asyncpg==0.30.0`
- `alembic==1.14.0`
- `greenlet==3.1.1`

`DATABASE_URL` shape: `postgresql+asyncpg://user:pass@postgres:5432/db`.
Alembic uses the sync driver (`postgresql+psycopg2`) — easier than async
migrations and standard practice. Both URLs are derived from one set of
env vars; we keep a single `DATABASE_URL` for the async engine and let
alembic build its sync URL from the same env in `alembic/env.py`.

Actually simpler: keep `DATABASE_URL` as the async URL; in `env.py`
strip `+asyncpg` so alembic uses default psycopg2.

## Alembic on startup

`main.py:lifespan` runs `command.upgrade(config, "head")` once before
yielding. Idempotent — alembic skips already-applied versions. We run it
inline rather than as a separate process to keep the dev stack a single
`make up`. For production this would move to an init container.

Alembic's `env.py` runs in **online** mode against the same database;
`run_migrations_online` uses `engine.begin()` and is synchronous, which
is fine in the lifespan because we only run it at startup.

## Endpoints

All under `/api/v1`:

| Verb   | Path                                                        | Body schema                                       | Response               |
|--------|-------------------------------------------------------------|---------------------------------------------------|------------------------|
| GET    | `/maintenance/operation-types`                              | —                                                 | `list[OperationType]`  |
| POST   | `/maintenance/operation-types`                              | `OperationTypeIn`                                 | `OperationType`        |
| PATCH  | `/maintenance/operation-types/{id}`                         | `OperationTypeUpdate`                             | `OperationType`        |
| DELETE | `/maintenance/operation-types/{id}`                         | —                                                 | 204                    |
| POST   | `/devices/{device_id}/maintenance/log`                      | `MaintenanceLogIn`                                | `MaintenanceLog`       |
| GET    | `/devices/{device_id}/maintenance/log`                      | params: from_date, to_date, page, page_size       | `list[MaintenanceLog]` |
| PATCH  | `/maintenance/log/{log_id}`                                 | `MaintenanceLogUpdate`                            | `MaintenanceLog`       |
| DELETE | `/maintenance/log/{log_id}`                                 | —                                                 | 204                    |

Pydantic schemas (`extra="forbid"`):

```python
class OperationTypeIn(BaseModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    description: str | None = None
    requires_component: bool = False

class OperationTypeUpdate(BaseModel):
    name: Annotated[str | None, StringConstraints(min_length=1, max_length=100)] = None
    description: str | None = None
    requires_component: bool | None = None
    # `model_validator` ensures at least one field is set.

class MaintenanceLogIn(BaseModel):
    operation_type_id: UUID
    performed_by_id: UUID | None = None
    start_time: datetime
    end_time: datetime | None = None
    component_path: str | None = None
    details_notes: str | None = None

class MaintenanceLogUpdate(BaseModel):
    operation_type_id: UUID | None = None
    performed_by_id: UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    component_path: str | None = None
    details_notes: str | None = None
```

`device_id` URL segment: same `to_urn`-style normalisation as devices —
404 on malformed.

## Error mapping

| Condition                                          | HTTP | Where checked                            |
|----------------------------------------------------|------|------------------------------------------|
| Malformed UUID in path                             | 404  | route                                    |
| Unknown device (Orion GET None)                    | 404  | route, on POST log                       |
| Unknown operation type FK                          | 422  | route, before INSERT                     |
| `requires_component=true` and missing path         | 422  | route                                    |
| `end_time < start_time`                            | 400  | route                                    |
| `from_date > to_date` on list                      | 400  | route                                    |
| Duplicate operation type name                      | 409  | catch IntegrityError on INSERT           |
| Delete operation type referenced by a log          | 409  | catch IntegrityError (FK RESTRICT)       |
| Bad pagination                                     | 422  | FastAPI Query                            |
| Empty PATCH body                                   | 422  | model_validator                          |

## Test plan

`tests/conftest.py`:

- `pg_clean` autouse fixture per test that TRUNCATEs both tables (cheap;
  isolates state). Uses a small `psycopg.connect` (sync) to avoid the
  test process needing the async stack.

`tests/test_maintenance.py` cases (≈ 17):

Operation types:
1. list_empty
2. create_then_list
3. create_duplicate_name_409
4. create_missing_name_422
5. patch_updates_fields
6. patch_unknown_404
7. delete_unknown_404
8. delete_referenced_409
9. delete_unreferenced_204

Maintenance log:
10. create_log_201_returns_row
11. create_log_unknown_device_404
12. create_log_unknown_operation_type_422
13. create_log_requires_component_missing_422
14. create_log_end_before_start_400
15. list_filters_by_date_range
16. list_pagination
17. patch_log_partial_updates
18. patch_log_unknown_404
19. patch_log_empty_body_422
20. delete_log_204
21. delete_log_unknown_404

## Risks / notes

- Running alembic in lifespan happens on every container start. With a
  single API replica that's fine. For multi-replica deployment we'd
  switch to an init container or a `make migrate` step.
- `psycopg2-binary` for Alembic vs `asyncpg` for runtime is two drivers.
  The disk cost is small; the alternative (running alembic via async)
  needs `alembic-utils`-style hacks and is not worth it.
- Tests use a sync `psycopg` to TRUNCATE — keeps the fixture simple and
  doesn't fight pytest-asyncio.
