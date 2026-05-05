# Journal — Ticket 0019b

## 2026-05-05 — In one sitting
- Started from the user ask: "after `make up` I want live data
  flowing through both MQTT and HTTP, no extra command".
- Picked the in-process route over a separate container: same
  `OrionClient`, same sessionmaker, same lifespan. ~280 LOC vs a
  whole new service + image + compose entry.
- Bootstrap is idempotent on stable UUIDv5 URNs. Reruns of `make up`
  hit the same five devices.

### Surprises while implementing
- The MQTT bridge caches subscriptions at `start()` and only refreshes
  on device CRUD via the API (in `routes/devices.py`). Since the
  simulator creates demo devices directly via Orion, the bridge
  never picked them up. Fix: simulator gets a reference to the
  bridge and calls `bridge.refresh()` after bootstrap.
- `dataTypes` shape gotcha: in 0018 the bridge expects a flat
  `{attr: "Number"}` dict, not `{attr: {"type": "Number"}}`. The
  full route validator (`validate_against_dataTypes`) does an exact
  equality check. Worth recording in `gotchas.md` if we ever surface
  a `dataTypes` editor in the UI (FU5 from 0019).
- First-create-then-PATCH-on-DuplicateEntity heals schema drift if a
  future simulator version changes the demo device shape — without
  it, an old running stack stays stuck on the first-version layout.
- `pg_clean` in the test conftest TRUNCATEs `device_ingest_keys`.
  The simulator caches cleartext keys in memory, so after a wipe
  it would 401 forever. Mitigated: on 401 we drop the cached key
  and re-mint on the next tick.

### Why HTTP loopback (not direct `apply_measurement`)
- Exercises the real route + auth + validation continuously. Any
  regression in `routes/ingest.py` shows up live in the UI rather
  than waiting for the next test run.
- Cost is one local TCP socket per tick, which is nothing.

### What `make up` looks like now
- 5 demo devices appear in `/devices` (`[demo] MQTT sensor 1..3`,
  `[demo] HTTP sensor 4..5`).
- Every ~10 s their `temperature` and `humidity` move (random walk
  inside realistic ranges).
- Both `/state` and `/telemetry` reflect them.
- The two HTTP demo devices have `device_ingest_keys` rows with
  `created_by="simulator"`. Operator-issued keys are never touched.

### Files touched
- new `platform/api/app/simulator.py` (~280 LOC)
- `platform/api/app/main.py` (lifespan wiring)
- `platform/api/app/config.py` (3 settings)
- `platform/compose/docker-compose.api.yml` (3 env vars)
- new ticket folder `agent-workflow/tickets/0019b-live-ingest-simulator/`
