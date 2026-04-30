# Design — 0004 telemetry-and-state

## Layout

New / changed files:

```
platform/api/app/
  config.py                # +quantumleap_url
  quantumleap.py           # NEW: async QL client
  deps.py                  # +QuantumLeapDep
  schemas_telemetry.py     # NEW: TelemetryEntry, TelemetryResponse, StateResponse
  routes/telemetry.py      # NEW: /devices/{id}/telemetry, /devices/{id}/state
  main.py                  # wire QL client + include telemetry router
platform/api/tests/
  test_telemetry.py        # NEW
  conftest.py              # +ql fixture, +DeviceMeasurement teardown
platform/.env.example      # +QUANTUMLEAP_URL
platform/compose/docker-compose.api.yml  # env passthrough + depends_on quantumleap
```

## QuantumLeap REST contract

QuantumLeap exposes (with the same Fiware headers as Orion):

```
GET /v2/entities/{entityId}
    ?type=DeviceMeasurement
    &attrs=numValue,unitCode
    &fromDate=<iso>&toDate=<iso>
    &lastN=<n>&limit=<n>&offset=<n>
```

Response shape:

```json
{
  "entityId": "urn:ngsi-ld:DeviceMeasurement:<uuid>:Temperature",
  "entityType": "DeviceMeasurement",
  "index": ["2026-04-30T12:00:00.000+00:00", ...],
  "attributes": [
    {"attrName": "numValue", "values": [25.4, ...]},
    {"attrName": "unitCode", "values": ["CEL", ...]}
  ]
}
```

`404` is returned when the measurement entity has no data yet — we
translate that to an empty-entries `200` response (so callers can poll
without special-casing first-time devices).

## Endpoint contracts

### `GET /api/v1/devices/{id}/telemetry`

| Query param          | Type            | Required | Validation                             |
|----------------------|-----------------|----------|----------------------------------------|
| `controlledProperty` | str             | yes      | non-empty, alphanumeric / `_`          |
| `fromDate`           | ISO-8601 dt     | no       | Pydantic `datetime`                    |
| `toDate`             | ISO-8601 dt     | no       | Pydantic `datetime`, ≥ `fromDate`      |
| `lastN`              | int             | no       | 1–1000                                 |
| `limit`              | int             | no       | 1–1000, default 100                    |
| `offset`             | int             | no       | ≥ 0, default 0                         |

Behaviour:

1. Normalise `id` to URN; 404 on malformed.
2. `GET /v2/entities/<deviceUrn>` against Orion → 404 if missing.
3. Build measurement URN
   `urn:ngsi-ld:DeviceMeasurement:<uuid>:<ControlledProperty>` (capitalise
   first letter to match `Temperature`, `Humidity`, `Battery`).
4. Query QL with the params above.
5. Zip `index` × `attributes[*].values` into entries. Drop entries where
   `numValue` is `None`.
6. `fromDate > toDate` → 400 (validated in route handler before calling
   QL).

Response:

```json
{
  "deviceId": "urn:ngsi-ld:Device:<uuid>",
  "controlledProperty": "temperature",
  "entries": [
    {"dateObserved": "2026-04-30T12:00:00Z", "numValue": 25.4, "unitCode": "CEL"}
  ]
}
```

### `GET /api/v1/devices/{id}/state`

1. Normalise id to URN; 404 on malformed.
2. `GET /v2/entities/<deviceUrn>` against Orion → 404 if missing.
3. Project: `{deviceState, dateLastValueReported, batteryLevel}`.
4. Omit attributes that are absent on the entity.

## Settings additions

```python
class Settings(BaseSettings):
    ...
    quantumleap_url: str = "http://quantumleap:8668"
```

`.env.example`:

```
QUANTUMLEAP_URL=http://quantumleap:8668
```

`docker-compose.api.yml` adds `QUANTUMLEAP_URL` to the env block and
`quantumleap` to `depends_on`.

## QuantumLeap client (sketch)

```python
class QuantumLeapClient:
    async def query_entity(self, entity_id, *, type_, attrs, from_date, to_date, last_n, limit, offset)
        -> dict | None  # None on 404
```

Returns `None` on 404 (no data), raises `QuantumLeapError` on other
non-200 statuses.

## Test plan

`tests/conftest.py` gains:

- `ql` fixture (httpx.Client to `QUANTUMLEAP_URL`, with Fiware headers).
- `created_measurement_ids` list that the teardown DELETEs from Orion.
- A small helper `push_measurement(orion_client, device_uuid, property,
  num_value, date_observed, unit_code=None)` that POSTs the measurement
  entity to Orion (`POST /v2/op/update` with `actionType=append`). The
  Orion → QL subscription propagates it to CrateDB asynchronously, so
  the helper polls QL up to ~5 s for the value to appear before
  returning.

### Cases — telemetry

1. `ingest_then_query_returns_entry`: push 3 measurements, GET telemetry,
   assert order, count, numValue, unitCode.
2. `query_empty_range_returns_empty_entries`: device exists, no
   measurements → 200 with `entries: []`.
3. `query_unknown_device_returns_404`.
4. `query_missing_controlled_property_returns_422`.
5. `query_bad_date_range_returns_400` (`fromDate` > `toDate`).
6. `query_lastN_limits_results`: push 5, `lastN=2` returns last 2.
7. `query_fromDate_filters_old_entries`: push 3 across two timestamps,
   verify the early one is excluded.

### Cases — state

8. `state_returns_subset_after_patch`: PATCH device with
   `deviceState=active`, GET state, assert that field present.
9. `state_unknown_device_returns_404`.
10. `state_no_optional_fields_returns_empty_object`.

## Risks / notes

- **CrateDB partitioning.** `data-model.md` quotes
  `ALTER TABLE … PARTITION BY (…)` as a one-shot DDL. CrateDB only
  accepts `PARTITIONED BY` on `CREATE TABLE`. The QL-managed table is
  therefore unpartitioned in this ticket. Fixing this requires either
  pre-creating the table before QL writes to it, or doing a copy-and-
  swap migration. Out of scope here; flagged in journal and as a
  follow-up.
- **QL ingestion latency.** Tests poll for up to 5 seconds. If CI gets
  flaky we'll bump the timeout, not skip the test.
- **Capitalisation of `controlledProperty` in URN.** We canonicalise to
  `Temperature`-style for the entity id; the API request and response
  remain lowercase.
