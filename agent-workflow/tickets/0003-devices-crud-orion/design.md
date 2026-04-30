# Design — 0003 Devices CRUD against Orion

## Layout

```
platform/api/
├── Dockerfile
├── requirements.txt          # + httpx, pytest
└── app/
    ├── main.py               # lifespan: open/close httpx client
    ├── config.py             # Settings (ORION_URL, FIWARE_SERVICE, FIWARE_SERVICEPATH, API_PREFIX)
    ├── orion.py              # OrionClient: thin httpx wrapper, raises typed errors
    ├── ngsi.py               # to_ngsi(payload) / from_ngsi(entity) translators
    ├── schemas.py            # Pydantic v2 models: DeviceIn / DeviceUpdate / DeviceOut + enums
    ├── errors.py             # HTTPException factories
    └── routes/
        ├── health.py
        └── devices.py        # /api/v1/devices

platform/api/tests/
├── conftest.py               # api_url, orion_url, http session, cleanup fixture
└── test_devices.py
```

## Schemas (Pydantic v2)

- `Category` enum: `sensor, actuator, gateway, plc, iotStation, endgun, weatherStation, other`.
- `Protocol` enum: `mqtt, coap, http, modbus, bacnet, lorawan, plc, other`.
- `DeviceState` enum: `active, inactive, maintenance`.

`DeviceIn` (POST body):
- Required: `name: str`, `category: Category`, `supportedProtocol: Protocol`.
- Optional: `id` (bare UUID or URN; absent → generated UUIDv4),
  `controlledProperty: list[str]`, `serialNumber: str`,
  `serialNumberType: str`, `location: {latitude: float, longitude: float}`,
  `address: dict`, `manufacturerName, modelName: str`,
  `dateInstalled: datetime`, `owner: list[str]`, `firmwareVersion: str`,
  `ipAddress: list[str]`, `deviceState: DeviceState`.
- Per-protocol attributes accepted at top level. A model-level validator
  enforces:
  - `mqtt` → `mqttTopicRoot`, `mqttClientId` required.
  - `plc`  → `plcIpAddress`, `plcPort`, `plcConnectionMethod`, `plcTagsMapping` required.
  - `lorawan` → `loraAppEui`, `loraDevEui`, `loraAppKey`, `loraNetworkServer`, `loraPayloadDecoder` required.
  - other protocols: no extra requireds.
- `extra = "forbid"` to surface typos as 422.

`DeviceUpdate` (PATCH body): every field optional, no per-protocol
required-fields rule, `extra = "forbid"`. `id`, `type` not patchable.

`DeviceOut` (response): same shape as `DeviceIn` plus `id` (URN) and
`type`. Absent attributes are omitted, not nulled.

## Id normalisation

```python
URN_PREFIX = "urn:ngsi-ld:Device:"
def to_urn(id_in: str | None) -> str:
    if id_in is None: id_in = str(uuid4())
    if id_in.startswith(URN_PREFIX): return id_in
    UUID(id_in)  # validate, raises ValueError → 422
    return URN_PREFIX + id_in
```

## NGSI translation

Single-direction mapping table keyed by attribute name; each entry
declares the NGSI type. Renderer (`to_ngsi`) wraps Python values in
`{type, value}` shape; `from_ngsi` extracts `value` for known attributes.

Type rules:
- `location` → NGSI `geo:point` with value `"<lat>,<lon>"`.
- `controlledProperty`, `owner`, `ipAddress` → `StructuredValue` (array).
- `address`, `dataTypes`, `mqttSecurity`, `plcCredentials`,
  `plcTagsMapping` → `StructuredValue` (object).
- `dateInstalled` → `DateTime` ISO 8601.
- numeric fields (`mqttQos`, `plcPort`, `plcReadFrequency`) → `Number`.
- everything else → `Text`.

Optional attributes are omitted from the rendered payload when absent.

## Orion client

Thin async wrapper over `httpx.AsyncClient`:

```python
class OrionClient:
    async def create_entity(payload) -> None       # 201 ok; 422 from Orion → DuplicateEntity
    async def get_entity(eid) -> dict | None       # None on 404
    async def list_entities(limit, offset) -> list[dict]
    async def patch_entity(eid, attrs) -> bool     # False on 404
```

All calls pass `Fiware-Service`, `Fiware-ServicePath` headers from
settings. Single client instance owned by FastAPI lifespan and exposed
via dependency `get_orion()`.

## Routes (`/api/v1/devices`)

| Method | Path             | Behaviour                                                                 |
|--------|------------------|---------------------------------------------------------------------------|
| POST   | `/`              | validate `DeviceIn`, normalise id, `to_ngsi`, `create_entity`, return 201 |
| GET    | `/`              | validate `limit`/`offset`, `list_entities`, return list of `DeviceOut`     |
| GET    | `/{id}`          | normalise id, `get_entity`, return `DeviceOut` or 404                     |
| PATCH  | `/{id}`          | validate `DeviceUpdate`, render attrs only, `patch_entity` or 404         |

Pagination validation: `limit ∈ [1,1000]`, `offset ≥ 0` → else 400.

`DELETE` not exposed (out of spec). Tests use Orion directly for cleanup.

## Settings

`platform/api/app/config.py` (pydantic-settings):

```
ORION_URL=http://orion:1026
FIWARE_SERVICE=iot
FIWARE_SERVICEPATH=/
API_PREFIX=/api/v1
```

Added to `platform/.env.example`.

## Tests (`make test`)

- Run inside the `iot-api` container: `docker compose ... exec iot-api pytest -v`.
- Test target URL: `http://iot-api:8000` (in-network) — base url from
  `API_INTERNAL_URL` env, default `http://localhost:8000`.
- Use `httpx.Client` (sync) for clarity.
- `conftest.py` provides:
  - `api`: `httpx.Client` rooted at the API.
  - `orion`: `httpx.Client` rooted at Orion (for cleanup only).
  - `created_ids`: list mutated by tests; teardown deletes each via Orion
    `DELETE /v2/entities/{id}` with the right service headers.
- Tests use unique UUIDs per case (`uuid4()`) → no cross-test pollution.

### Test cases

1. `test_create_minimal_returns_201_with_urn_id`
2. `test_create_with_explicit_uuid_returns_urn`
3. `test_create_full_mqtt_device_round_trips`
4. `test_create_missing_name_returns_422`
5. `test_create_unknown_category_returns_422`
6. `test_create_mqtt_without_topic_root_returns_422`
7. `test_create_plc_without_required_fields_returns_422`
8. `test_create_lorawan_without_required_fields_returns_422`
9. `test_create_extra_field_returns_422`
10. `test_create_duplicate_returns_409`
11. `test_get_by_uuid_and_by_urn_match`
12. `test_get_unknown_returns_404`
13. `test_list_empty_when_no_devices` *(skipped if env not clean)*
14. `test_list_after_creates_includes_them`
15. `test_list_pagination_bad_limit_returns_400`
16. `test_patch_partial_updates_only_given_fields`
17. `test_patch_unknown_returns_404`
18. `test_patch_extra_field_returns_422`

## Dependencies added

`platform/api/requirements.txt`:
- `httpx==0.28.1`
- `pydantic-settings==2.7.1`
- `pytest==8.3.4`

(No SQLAlchemy / Alembic / multipart this ticket — those land with later
tickets that need them.)

## Makefile additions

```
test: check-env  ## Run API integration tests against the running stack
	$(DC) exec -T iot-api pytest -v
```

## Risks / notes

- Orion returns 422 (NGSI v2) on duplicate id — our route maps it to 409.
- Orion's `keyValues` representation is **not** used; we exchange full
  normalised entities so types are explicit and round-trip safe.
- `geo:point` value is `"lat,lon"` (Orion convention).
- `extra = "forbid"` on schemas catches typos early; this is by design.
- Tests assume `make up` is running; `make test` does not start the stack.