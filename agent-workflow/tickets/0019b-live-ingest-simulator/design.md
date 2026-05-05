# Design — Live Ingest Simulator

## Approach
A single new module `app/simulator.py` exposing `LiveSimulator` with
`start(loop, orion, sessionmaker)` / `stop()`, mirroring the
`MqttBridge` lifecycle pattern. Started from the existing `lifespan`
in `app/main.py` after the bridge.

### Bootstrap (idempotent)
On `start()`, the simulator ensures 5 entities exist in Orion via
`OrionClient.create_entity` (NGSI v2 has no auth, so no Keycloak
detour). Stable URNs:

```
namespace = uuid.UUID("00000000-0000-0000-0000-0000000051ed")
demo_id(n) = f"urn:ngsi-ld:Device:{uuid.uuid5(namespace, f'demo-{n}')}"
```

Layout:
- `demo-1..3`: `supportedProtocol="mqtt"`, `mqttTopicRoot="demo/sensor-N"`,
  `mqttClientId="demo-N"`, `dataTypes={"temperature":{"type":"Number"},
  "humidity":{"type":"Number"}}`, `controlledProperty=["temperature","humidity"]`.
- `demo-4..5`: `supportedProtocol="http"`, `controlledProperty=["temperature","humidity"]`.

If `OrionClient.create_entity` says "already exists" (422), we
treat it as success.

### Tick loop
Every `simulator_interval_seconds` (default 10) the task:
1. Lists all devices via `OrionClient.list_entities`.
2. For each device whose URN belongs to the demo namespace:
   - For MQTT: paho `publish(f"{root}/{attr}", json.dumps({"value": v}))`.
   - For HTTP: ensure ingest key (see below), POST to `/telemetry`.

Random-walk values per `(device, attr)` clamped to a realistic range
(reusing the table from `add_test_data.py`).

### HTTP key ownership
At startup, for each HTTP demo device:
- Look up `device_ingest_keys` by uuid.
- If missing → mint a new key, hash it, insert row with `created_by="simulator"`.
- If present and `created_by="simulator"` → it's ours but we don't
  know the cleartext (only hashes are stored). Rotate: update the
  same row with a fresh hash + cache the new cleartext in memory.
- If present and `created_by != "simulator"` → skip this device for
  the simulator (log once at WARNING). Operator owns the key.

### Settings (`app/config.py`)
```python
simulator_enabled: bool = False
simulator_interval_seconds: int = 10
simulator_api_base_url: str = "http://localhost:8000"
```

`docker-compose.api.yml` adds:
```yaml
- SIMULATOR_ENABLED=${SIMULATOR_ENABLED:-true}
- SIMULATOR_INTERVAL_SECONDS=${SIMULATOR_INTERVAL_SECONDS:-10}
- SIMULATOR_API_BASE_URL=http://localhost:8000
```

### Lifecycle
```python
# main.py lifespan, after MqttBridge
sim: LiveSimulator | None = None
if settings.simulator_enabled:
    sim = LiveSimulator(settings)
    await sim.start(loop, app.state.orion, app.state.sessionmaker)
…
finally:
    if sim is not None: await sim.stop()
```

## Why not a separate container
- Reuses `OrionClient` and the asyncpg sessionmaker. No new image,
  no new compose service, no new dependency wiring.
- The simulator is Python-only and small (~250 LOC); fits naturally
  alongside `MqttBridge`, which is the most analogous existing piece.

## Why HTTP loopback (not direct `apply_measurement`)
- Exercises the real route + auth + validation continuously: any
  regression in `routes/ingest.py` shows up live in the UI.
- Costs almost nothing (in-process ASGI server, single httpx connection).

## Risks
- **Test interference**: simulator might mutate devices tests care
  about. Mitigated: simulator only acts on demo URNs (UUIDv5 from
  fixed namespace); off by default in `Settings`. Tests in CI keep
  the off default.
- **Race during early startup**: simulator first tick happens 5 s
  after lifespan-yield to let uvicorn bind. Connect failures retry
  on the next tick.
- **Operator-issued key rotation**: explicitly disallowed (see above).

## Test strategy
No new pytest suite — the simulator is a dev/demo conveyor and is
covered indirectly by the existing 0018/0019 tests. Manual smoke:

```bash
make up
# wait ~30 s
curl -s http://localhost:8001/api/v1/devices | jq '.items[] | select(.name|startswith("[demo]")) | .id'
DEV=...   # pick one
curl -s "http://localhost:8001/api/v1/devices/$DEV/state" | jq
curl -s "http://localhost:8001/api/v1/devices/$DEV/telemetry?controlledProperty=temperature&limit=5" | jq
```

## Affected files
- new `platform/api/app/simulator.py`
- `platform/api/app/main.py` (lifespan wiring)
- `platform/api/app/config.py` (3 new settings)
- `platform/compose/docker-compose.api.yml` (3 new env vars)
- `platform/.env.example` + `platform/.env` (note keys; defaults
  baked in compose so optional)
