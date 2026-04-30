# Tasks — 0005 maintenance-log

- [x] Add SQLAlchemy[asyncio], asyncpg, alembic, greenlet, psycopg2-binary, psycopg[binary] to `requirements.txt`.
- [x] `app/config.py`: add `database_url`.
- [x] `app/db.py`: async engine + sessionmaker + `Base`.
- [x] `app/models_maintenance.py`: SQLAlchemy 2.0 models for both tables, FK ON DELETE RESTRICT, three indexes.
- [x] `app/schemas_maintenance.py`: Pydantic v2 models with `extra=forbid` and "at least one field" validators on PATCH bodies.
- [x] `app/deps.py`: `SessionDep`.
- [x] Alembic scaffolding: `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/0001_initial_maintenance.py`.
- [x] `app/routes/maintenance.py`: 8 endpoints (operation-types CRUD + log CRUD).
- [x] `app/main.py`: run alembic upgrade in lifespan; wire engine/sessionmaker; include router.
- [x] Dockerfile: COPY alembic + alembic.ini.
- [x] docker-compose.api.yml: `DATABASE_URL` env, mounts, `depends_on: postgres`.
- [x] `.env.example`: documented `DATABASE_URL`.
- [x] Extend `tests/conftest.py` with autouse `pg_clean` fixture.
- [x] `tests/test_maintenance.py`: 24 behaviour tests.
- [x] Run `make up && make test` — 55/55 green.
- [x] Update roadmap.
- [x] Commit + push.
