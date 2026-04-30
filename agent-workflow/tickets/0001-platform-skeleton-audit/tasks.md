# Tasks — Ticket 0001 Platform skeleton audit

Goal-driven; tick as each verifiable check passes.

## Skeleton
- [x] Create `platform/api/Dockerfile` (python:3.13-slim, fixed `COPY`).
- [x] Create `platform/api/requirements.txt` (fastapi, uvicorn, pydantic v2, python-dotenv).
- [x] Create `platform/api/app/main.py` (FastAPI app, includes health router).
- [x] Create `platform/api/app/routes/health.py` (`GET /healthz` → `{"status":"ok"}`).
- [x] Create `platform/api/app/__init__.py` and `platform/api/app/routes/__init__.py`.
- [x] Create `platform/config/cratedb/crate.yml` (copy from context).

## Compose
- [x] Create `platform/compose/docker-compose.base.yml` with cratedb 6.2.6, orion 4.4.0, mongo 8.2.7, postgres 17.9, quantumleap 1.0.0; bake `CRATE_HEAP_SIZE=2g` default.
- [x] Create `platform/compose/docker-compose.api.yml` (build context `../api`, bind mount, `API_PORT:8000`).
- [x] Create `platform/.env.example` (NETWORK_NAME, CRATEDB_PORT, ADMIN_UI_PORT, POSTGRES_*, API_PORT, QL knobs).

## Bootstrap
- [x] Create `platform/scripts/setup_orion_subscription.sh` — minimal idempotent: wait for Orion+QL `/version`, POST subscription (skip if 409). No demo sensor, no test data.
- [x] Mark script executable (`chmod +x`).

## Makefile
- [x] Create root `Makefile` with: `help up down logs ps restart bootstrap clean`. `clean` requires `CONFIRM=1`.

## Docs
- [x] Replace stub `agent-workflow/architecture.md` with chosen layout + version table.
- [x] Create `context/platform/README.md` frozen-reference note.

## Verification
- [x] `cp platform/.env.example platform/.env`
- [x] `make bootstrap` → exit 0; all 5 services Up.
- [x] `make ps` shows 5 healthy services.
- [x] `curl -fsS http://localhost:$API_PORT/healthz` → `{"status":"ok"}`.
- [x] `curl -fsS http://localhost:1026/version` → 200.
- [x] `curl -fsS http://localhost:8668/version` → 200.
- [x] `make down` → exit 0.

## Wrap-up
- [x] Fill `journal.md` with chosen versions + any compatibility surprises.
- [x] Fill `review.md` self-review.
- [x] Flip `status.md` to `done` after user accepts.
