# Target Architecture

> Living document. Updated by every ticket that changes structure or
> infrastructure. Source of truth for product requirements remains
> `context/doc/backend.md` (Spanish). The data model (NGSI entity types,
> attribute names, telemetry conventions, CrateDB partitioning) is pinned
> in [`data-model.md`](data-model.md).

## Repo layout

Reflects the state of `main` after ticket 0018a (2026-05-05).

```
.
├── Makefile                  # Top-level control surface (make help)
├── AGENTS.md
├── agent-workflow/           # Spec-driven workflow (tickets, memory, this doc)
├── context/
│   ├── doc/                  # Product spec (Spanish, source of truth)
│   └── platform/             # FROZEN — bootstrap reference, do not modify
├── platform/                 # Live dev stack
│   ├── api/                  # FastAPI service (build context)
│   │   ├── Dockerfile
│   │   ├── alembic/          # Postgres migrations
│   │   ├── alembic.ini
│   │   ├── requirements.txt
│   │   ├── pytest.ini
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py     # Settings (env-driven)
│   │   │   ├── deps.py       # OrionDep, QuantumLeapDep, DBSession
│   │   │   ├── auth.py       # JWT validation, require_roles()
│   │   │   ├── middleware.py # RequestId, errors
│   │   │   ├── db.py
│   │   │   ├── ngsi.py       # NGSI v2 (de)serialisation
│   │   │   ├── orion.py      # OrionClient
│   │   │   ├── quantumleap.py
│   │   │   ├── mqtt_bridge.py    # in-process MQTT → Orion bridge
│   │   │   ├── mqtt_payload.py   # parse / infer / validate payloads
│   │   │   ├── floorplans.py     # site-area floor-plan storage
│   │   │   ├── manuals.py        # PDF manual storage
│   │   │   ├── models_*.py       # SQLAlchemy models
│   │   │   ├── schemas*.py       # Pydantic schemas
│   │   │   └── routes/
│   │   │       ├── health.py     # GET /healthz
│   │   │       ├── devices.py    # /devices CRUD (Orion-backed)
│   │   │       ├── telemetry.py  # /devices/{id}/telemetry, /state
│   │   │       ├── maintenance.py
│   │   │       ├── operation_types.py # via maintenance.py
│   │   │       ├── manuals.py
│   │   │       ├── floorplans.py
│   │   │       ├── me.py         # /me identity echo
│   │   │       └── system.py     # /system/mqtt (admin)
│   │   └── tests/                # pytest suite (~170 tests)
│   ├── compose/
│   │   ├── docker-compose.base.yml   # core stack + mosquitto + keycloak
│   │   └── docker-compose.api.yml    # iot-api + oauth2-proxy overlay
│   ├── config/
│   │   ├── cratedb/crate.yml
│   │   ├── keycloak/realm-iot.json   # imported on first boot
│   │   └── mosquitto/{mosquitto.conf,passwd}  # passwd is git-ignored
│   └── scripts/
│       ├── add_test_data.py          # `make seed`
│       └── setup_orion_subscription.sh
└── web/                              # Next.js 14 App Router + Tailwind
    ├── src/{app,components,i18n,lib}/
    └── ...
```

## Service stack

External Docker network `iot-net` (created by `make up` if missing).
After 0013b, only **oauth2-proxy** publishes a host port; everything
else is reachable through it as a single origin.

| Service        | Image                                  | Host port           | Purpose                                    |
|----------------|----------------------------------------|---------------------|--------------------------------------------|
| cratedb        | `crate:6.2.6`                          | 4200, 5432          | Time-series store for QuantumLeap          |
| postgres       | `postgres:17.9`                        | 127.0.0.1:5433      | Maintenance log, manuals, floorplans, …    |
| mongo          | `mongo:8.2.7`                          | (internal)          | Orion context-broker backend               |
| orion          | `fiware/orion:4.4.0`                   | (internal)          | NGSI v2 context broker                     |
| quantumleap    | `orchestracities/quantumleap:1.0.0`    | (internal)          | NGSI → CrateDB persister                   |
| mosquitto      | `eclipse-mosquitto:2.0`                | 127.0.0.1:1883      | MQTT broker (password-file auth, no TLS)   |
| keycloak-db    | `postgres:17`                          | (internal)          | Keycloak's own Postgres                    |
| keycloak       | `quay.io/keycloak/keycloak:24`         | 127.0.0.1:8081      | Realm `iot-platform`, OIDC for the edge    |
| oauth2-proxy   | `quay.io/oauth2-proxy/oauth2-proxy`    | 127.0.0.1:${WEB_PORT} (default 80) | Single host-facing edge: `/api/*` → iot-api, `/*` → web |
| iot-api        | local build (`python:3.13-slim`)       | none (internal only)| Platform REST API                          |
| web            | local build (Next.js dev server)       | none (internal only)| UI                                         |

## API runtime

- Python 3.13, FastAPI 0.136, Uvicorn 0.46, Pydantic 2.13, SQLAlchemy
  + Alembic for the Postgres side, `httpx` for Orion / QuantumLeap,
  `paho-mqtt==2.1.0` for the bridge.
- Routes mounted under `settings.api_prefix` (default `/api/v1`):
  - `GET /healthz` (legacy liveness; `/system/health` will replace it
    in 0026).
  - `GET/POST/PATCH/DELETE /devices` and `/devices/{id}` (Orion-backed
    CRUD; protocol-extension validation per 0006).
  - `GET /devices/{id}/state`, `GET /devices/{id}/telemetry`
    (current state via Orion; history via QuantumLeap from
    `DeviceMeasurement` entities).
  - `GET/POST/PATCH/DELETE /devices/{id}/maintenance/log`,
    `/maintenance/log/{id}`,
    `/maintenance/operation-types[...]`.
  - `GET/POST/DELETE /devices/{id}/manuals`,
    `GET /manuals/{id}` (inline / download).
  - `GET/POST/DELETE /sites/{siteArea}/floorplan` and
    `/devices/{id}/placement` (per 0017).
  - `GET /me` (identity + roles echo, per 0015).
  - `GET /system/mqtt` (admin-only bridge stats, per 0018).
- Cross-cutting: `RequestIdMiddleware` + global `Exception` handler
  log via `app.errors` and return `{detail, request_id}` with a
  matching `X-Request-ID` header (per 0010).

## Auth

- **Keycloak** realm `iot-platform` imported from
  `platform/config/keycloak/realm-iot.json`. Four realm roles:
  `viewer`, `operator`, `maintenance_manager`, `admin`. Seed users
  for each (per 0013).
- **oauth2-proxy** sits in front of both Next.js and FastAPI as the
  only host-facing port; same-origin fetches replace cross-origin
  CORS plumbing (per 0013b).
- **FastAPI** validates JWTs against Keycloak's JWKS and exposes a
  `require_roles(*roles)` dependency; RBAC matrix in `backend.md`
  is enforced on every route shipped in 0003–0008 (per 0014).
- **Web** reads identity + roles via `/me`, hides forbidden actions,
  redirects role-restricted pages, and surfaces 401/403 as
  re-login / Spanish toast (per 0015).
- **Local dev only**: no TLS; oauth2-proxy and Keycloak both bound
  to `localhost`. Production TLS / Let's Encrypt is 0028.

## Ingestion (current state, 2026-05-05)

- **MQTT**: `MqttBridge` (in-process, paho thread + asyncio loop)
  subscribes to `<mqttTopicRoot>/+` per MQTT-enabled device, parses
  the payload, and validates against the device's `dataTypes`. Each
  successful publish performs a **dual write** against Orion (closed
  by 0018b):
    1. `PATCH Device:<id>` with `{<attr>: ..., dateLastValueReported:
       <utc-now>}` — what `GET /devices/{id}/state` reads.
    2. Only when the attribute is `Number`, upsert
       `urn:ngsi-ld:DeviceMeasurement:<deviceUuid>:<Attr>` carrying
       `refDevice`, `controlledProperty`, `numValue`, `dateObserved`
       (`unitCode` is omitted for now, optional per the data model)
       — what `GET /devices/{id}/telemetry` reads via QuantumLeap.
  The upsert pattern is `POST /v2/entities` first, falling back to
  `POST /v2/entities/<id>/attrs` on duplicate, mirroring
  `add_test_data.py`. Failures of the measurement upsert are logged
  at WARNING and never roll back the `Device` patch — `/state`
  freshness is treated as more critical than telemetry consistency
  in v1. Future ingest paths (HTTP / LoRaWAN webhook from 0019)
  will reuse `MqttBridge._upsert_measurement` as the canonical
  writer.
- **HTTP / LoRaWAN webhook**: not yet implemented (0019).
- **Seed data**: `platform/scripts/add_test_data.py` (`make seed`)
  pushes synthetic telemetry directly through Orion → QL so the UI
  has data without needing real sensors.

## Control surface

| Command            | Effect                                                     |
|--------------------|------------------------------------------------------------|
| `make up`          | Build + start the full stack in the background             |
| `make down`        | Stop the stack (volumes preserved)                         |
| `make logs`        | Tail logs of all services                                  |
| `make ps`          | List service status                                        |
| `make restart`     | `down` + `up`                                              |
| `make bootstrap`   | `up` then register Orion → QL subscription (idempotent)    |
| `make seed`        | Populate ~50 devices + maintenance + telemetry             |
| `make test`        | Run the API pytest suite against the live stack            |
| `make mqtt-password` | Regenerate `platform/config/mosquitto/passwd` from env   |
| `make secrets-keycloak` | Regenerate Keycloak client secrets                    |
| `make logs-keycloak` / `make logs-oauth2-proxy` | Service-scoped logs           |
| `make clean`       | DESTRUCTIVE: drop volumes (requires `CONFIRM=1`)           |
