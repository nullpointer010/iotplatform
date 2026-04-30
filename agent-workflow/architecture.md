# Target Architecture

> Living document. Updated by every ticket that changes structure or
> infrastructure. Source of truth for product requirements remains
> `context/doc/backend.md` (Spanish).

## Repo layout

```
.
├── Makefile                  # Top-level control surface (make help)
├── AGENTS.md
├── agent-workflow/           # Spec-driven workflow (tickets, memory, this doc)
├── context/                  # Product spec + frozen reference draft
│   └── platform/             # FROZEN — bootstrap reference, do not modify
└── platform/                 # Live dev stack
    ├── .env.example
    ├── api/                  # FastAPI service (build context)
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── app/
    │       ├── main.py
    │       └── routes/
    │           └── health.py # GET /healthz
    ├── compose/
    │   ├── docker-compose.base.yml
    │   └── docker-compose.api.yml
    ├── config/
    │   └── cratedb/crate.yml
    └── scripts/
        └── setup_orion_subscription.sh
```

## Service stack (ticket 0001)

| Service     | Image                                  | Purpose                        |
|-------------|----------------------------------------|--------------------------------|
| cratedb     | `crate:6.2.6`                          | Time-series store for QL       |
| postgres    | `postgres:17.9`                        | Relational store (future use)  |
| mongo       | `mongo:8.2.7`                          | Orion context broker backend   |
| orion       | `fiware/orion:4.4.0`                   | NGSI v2 context broker         |
| quantumleap | `orchestracities/quantumleap:1.0.0`    | NGSI -> CrateDB persister      |
| iot-api     | local build (`python:3.13-slim`)       | Platform REST API              |

All services share the external Docker network `iot-net` (created by
`make up` if missing).

## API runtime

- Python 3.13, FastAPI 0.136, Uvicorn 0.46, Pydantic 2.13.
- Single endpoint so far: `GET /healthz` -> `{"status":"ok"}`.

## Control surface

| Command          | Effect                                                     |
|------------------|------------------------------------------------------------|
| `make up`        | Build + start the full stack in the background             |
| `make down`      | Stop the stack (volumes preserved)                         |
| `make logs`      | Tail logs of all services                                  |
| `make ps`        | List service status                                        |
| `make restart`   | `down` + `up`                                              |
| `make bootstrap` | `up` then register Orion -> QL subscription (idempotent)   |
| `make clean`     | DESTRUCTIVE: drop volumes (requires `CONFIRM=1`)           |
