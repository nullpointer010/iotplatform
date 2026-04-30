# Journal — Ticket 0001

## Decisions

- **Layout:** Top-level `Makefile` + `platform/{api,compose,config,scripts}/`,
  with `context/platform/` frozen as historical reference (per requirements Q1).
- **Image versions** picked as latest stable as of 2026-04:
  | Service     | Old (frozen)                          | New (live)                            |
  |-------------|---------------------------------------|---------------------------------------|
  | cratedb     | `crate:5.6.2`                         | `crate:6.2.6`                         |
  | postgres    | `postgres:16`                         | `postgres:17.9`                       |
  | mongo       | `mongo:6.0`                           | `mongo:8.2.7`                         |
  | orion       | `fiware/orion:3.10.1`                 | `fiware/orion:4.4.0`                  |
  | quantumleap | `orchestracities/quantumleap:0.8.3`   | `orchestracities/quantumleap:1.0.0`   |
- **Python runtime:** `python:3.13-slim` (was 3.9-slim).
- **API deps bumped:** FastAPI 0.136.1, Uvicorn[standard] 0.46.0,
  Pydantic 2.13.3, python-dotenv 1.0.1. SQLAlchemy/cratedb-driver dropped
  for now — no DB code yet, will reintroduce when first persistent route
  lands.
- **Routes:** removed `/test` and `/dummy` placeholder routers; replaced
  with a single `GET /healthz` returning `{"status":"ok"}`.
- **Bootstrap:** split the original `bootstrap.sh`. `make bootstrap` owns
  network + compose; `setup_orion_subscription.sh` owns only the idempotent
  QL subscription. The 5-update demo loop and hard-coded `test_sensor_001`
  entity were dropped (not needed for the skeleton).

## Compatibility findings

- **Orion 4.x dropped `-dbhost`.** Original draft used
  `command: -dbhost mongo-db -logLevel INFO`, but Orion 4.4.0 fails with
  `parameter 'mongo-db' not recognized`. Fixed via
  `-dbURI mongodb://mongo-db:27017 -logLevel INFO`.
- **Orion does not return 409 on duplicate subscriptions.** Each POST
  creates a new subscription with a fresh ID, so a naive "201-or-409"
  idempotency check drifts on re-runs. Fixed via GET-then-POST: list
  current subscriptions, grep for the QL notify URL, skip if present.
- All other services started cleanly on first try with the bumped tags.

## Verification

`make bootstrap` (twice — second run idempotent: "Subscription already
exists; skipping.") → `make ps` shows 6 services Up. `curl /healthz` →
`{"status":"ok"}`. `curl /version` on Orion (1026) and QuantumLeap (8668)
both 200. `make down` exits clean.
