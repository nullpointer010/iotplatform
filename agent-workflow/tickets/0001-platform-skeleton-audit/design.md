# Design — Ticket 0001 Platform skeleton audit

## Approach
Restructure (not promote, not replace) the legacy `context/platform/` draft
into a clean top-level `platform/` directory, owned by the Makefile. Keep the
same service set (FastAPI API + CrateDB + FIWARE Orion + QuantumLeap + MongoDB
+ PostgreSQL) and the same network topology (one external Docker network), but
fix the broken bits, bump images to current stable versions, and replace the
`bootstrap.sh` orchestration with `make` targets.

`context/platform/` stays in place verbatim as a historical reference; a tiny
README note marks it frozen.

## Alternatives considered
- **A) Promote `context/platform/` as-is (rename to `platform/`).** Rejected:
  the Dockerfile is broken (`COPY ../ ./` reaches outside the build context),
  Python/FastAPI/Pydantic versions are 3+ years old, and `bootstrap.sh` mixes
  network creation, compose, and Orion subscription provisioning in one
  non-idempotent script.
- **B) Replace with a from-scratch Helm/Kubernetes layout.** Rejected: out of
  scope for Phase 1; the spec calls for Docker Compose dev stack first.

## Chosen layout
```
platform/
  api/
    Dockerfile
    requirements.txt
    app/
      main.py
      routes/
        health.py               # GET /healthz
  compose/
    docker-compose.base.yml     # crate, orion, mongo, postgres, quantumleap
    docker-compose.api.yml      # iot-api (overlay; merged with base)
  config/
    cratedb/
      crate.yml                 # copied verbatim from context/platform
  scripts/
    setup_orion_subscription.sh # idempotent; creates QL subscription on demand
  .env.example
Makefile                        # at REPO ROOT (per "better Makefile to run all")
```

Rationale:
- `platform/` is the runtime artefact; everything inside is consumed by Docker.
- `Makefile` at the repo root is the single human entry point — matches the
  user's "better Makefile to run all" request and lets `make` work from any
  fresh clone without `cd`.
- `compose/` subdir keeps base + overlay together and is what `make` points
  `-f` at.
- `scripts/setup_orion_subscription.sh` is kept as a shell script (it is just
  three `curl`s) but is invoked by `make bootstrap`, never by users directly.

## Image versions (latest stable as of 2026-04, verified on Docker Hub / PyPI)
| Service       | Image                            | Old (context)         | New (this ticket)      |
|---------------|----------------------------------|-----------------------|------------------------|
| CrateDB       | `crate`                          | `5.6.2`               | `6.2.6`                |
| FIWARE Orion  | `fiware/orion`                   | `3.10.1`              | `4.4.0`                |
| QuantumLeap   | `orchestracities/quantumleap`    | `0.8.3`               | `1.0.0`                |
| MongoDB       | `mongo`                          | `6.0`                 | `8.2.7`                |
| PostgreSQL    | `postgres`                       | `16`                  | `17.9`                 |
| Python base   | `python`                         | `3.9-slim`            | `3.13-slim`            |

Python deps (in `platform/api/requirements.txt`):
| Package                | Old             | New                |
|------------------------|-----------------|--------------------|
| `fastapi`              | `0.95.2`        | `0.136.1`          |
| `uvicorn[standard]`    | `0.22.0`        | `0.46.0`           |
| `pydantic`             | `1.10.7` (v1!)  | `2.13.3` (v2)      |
| `python-dotenv`        | `dotenv 0.9.9` (wrong pkg) | `python-dotenv 1.0.1` |
| `pytz`                 | `2024.1`        | drop (Python 3.13 has `zoneinfo`) |
| `sqlalchemy`           | `2.0.44`        | drop for this ticket — no DB calls in `/healthz` |
| `sqlalchemy-cratedb`   | `0.41.0`        | drop for this ticket — reintroduce when first DB-touching ticket lands |

Notes:
- QuantumLeap `1.0.0` is the latest published tag (project moves slowly; this
  is still its current stable).
- Postgres `17.9` chosen over `18` because `18` is brand-new; `17.x` is the
  most recent battle-tested major and aligns with what the FIWARE ecosystem
  generally validates against.
- CrateDB pinned at full `6.2.6` (not floating `6.2`) to avoid silent jumps.

## Dockerfile fix
Old:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY ../ ./        # broken: outside build context
```
New (`platform/api/Dockerfile`, build context = `platform/api`):
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Dev override (live reload + bind mount) lives in `docker-compose.api.yml`, not
in the image.

## Routes
- Drop legacy `/test` and `/dummy` (placeholders).
- Add a single `GET /healthz` returning `{"status": "ok"}`. This satisfies the
  acceptance criterion "200 + JSON body" with a meaningful, long-lived
  endpoint.

> **Deviation from requirements** — the requirements list `/dummy`. Replacing
> it with `/healthz` is a strict improvement (semantic, kept long-term) and
> the criterion "200 + JSON body" is still met. If the user prefers literal
> `/dummy`, ping back at the gate.

## Makefile (root)
| Target          | Action                                                                 |
|-----------------|------------------------------------------------------------------------|
| `make help`     | List targets (default).                                                |
| `make up`       | `docker compose -f platform/compose/...base.yml -f ...api.yml up -d --build` |
| `make down`     | `docker compose ... down`                                              |
| `make logs`     | `docker compose ... logs -f --tail=100`                                |
| `make ps`       | `docker compose ... ps`                                                |
| `make restart`  | `down` + `up`                                                          |
| `make bootstrap`| Ensure external network exists, `up`, then run `setup_orion_subscription.sh`. First-run target. |
| `make clean`    | `down -v` (drops volumes — destructive, requires `CONFIRM=1`).         |

Implementation details:
- `--env-file platform/.env` loaded via Compose, not via Make.
- External network name read from `.env` (`NETWORK_NAME=iot-net`); created
  with `docker network create $$NETWORK_NAME 2>/dev/null || true` inside
  `make bootstrap`.

## .env.example
Keep: `NETWORK_NAME`, `CRATEDB_PORT`, `ADMIN_UI_PORT`, `POSTGRES_*`,
`API_PORT` (default `80`).
Drop `CRATE_HEAP_SIZE` knob — bake a sensible default into
`docker-compose.base.yml`; users can still override.

## Frozen reference note
Add `context/platform/README.md`:
> Frozen reference draft from project bootstrap. Superseded by `/platform/`
> at repo root. Do not modify; do not run.

## Affected files / new files
- **New:** `Makefile`, `platform/api/Dockerfile`, `platform/api/requirements.txt`,
  `platform/api/app/main.py`, `platform/api/app/routes/health.py`,
  `platform/compose/docker-compose.base.yml`,
  `platform/compose/docker-compose.api.yml`,
  `platform/config/cratedb/crate.yml`,
  `platform/scripts/setup_orion_subscription.sh`,
  `platform/.env.example`, `context/platform/README.md`.
- **Modified:** `agent-workflow/architecture.md` (replace stub with chosen
  layout + version table).
- **Untouched:** everything under `context/platform/*` (frozen).

## Data model / API contract changes
None. `/healthz` returns `{"status": "ok"}` with HTTP 200; no other contract.

## Risks
- **Image drift** (e.g. QuantumLeap 1.0.0 incompatible with Orion 4.4.0).
  → `make bootstrap` exits non-zero if the QL→CrateDB subscription POST fails;
  `journal.md` records compatibility findings. If broken, fall back one minor
  on the offending image and re-pin.
- **Slow first boot** can race the Orion subscription script.
  → `setup_orion_subscription.sh` polls `/version` endpoints with retries.
- **Pydantic v1 → v2** is a major jump; not a risk here (no models defined),
  flagged for ticket 0002+.
- **Port 80 default for API** can clash with host services.
  → `.env.example` documents `API_PORT`.

## Test strategy for this ticket
- **Manual verification (mandatory):**
  1. `cp platform/.env.example platform/.env`
  2. `make bootstrap`
  3. `make ps` — all 5 services `Up`/`healthy`.
  4. `curl -fsS http://localhost:$$(grep API_PORT platform/.env | cut -d= -f2)/healthz` → `{"status":"ok"}`.
  5. `curl -fsS http://localhost:1026/version` (Orion) → 200.
  6. `curl -fsS http://localhost:8668/version` (QuantumLeap) → 200.
  7. `make down` — all services stop cleanly.
- **Unit / integration tests:** none in this ticket. Test infrastructure is
  ticket 0003.
