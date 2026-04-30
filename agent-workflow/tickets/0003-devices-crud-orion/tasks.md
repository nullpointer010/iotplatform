# Tasks — 0003 devices CRUD against Orion

- [x] Add `httpx`, `pydantic-settings`, `pytest` to `platform/api/requirements.txt`.
- [x] `app/config.py`: pydantic-settings `Settings` (orion_url, fiware_service, fiware_servicepath, api_prefix).
- [x] `app/schemas.py`: `DeviceIn` / `DeviceUpdate` with enums, GeoPoint, protocol-specific validators, URN id normalisation, `extra=forbid`.
- [x] `app/ngsi.py`: API JSON ↔ NGSI v2 normalised entity translation (geo:point, StructuredValue, DateTime, Number, Text).
- [x] `app/orion.py`: `OrionClient` with create/get/list/patch + `DuplicateEntity`, `OrionError`. PATCH uses `POST /v2/entities/{id}/attrs` (append-or-update) to avoid Orion's `PartialUpdate` 422.
- [x] `app/deps.py`: `OrionDep` from `app.state`.
- [x] `app/routes/devices.py`: POST/GET/list/PATCH endpoints; URN normalisation; mapping 404/409/422.
- [x] `app/main.py`: lifespan opens shared `httpx.AsyncClient`; mounts devices router under `api_prefix`.
- [x] `tests/conftest.py`: `api`, `orion`, `created_ids` fixtures (cleanup via Orion DELETE).
- [x] `tests/test_devices.py`: 19 behaviour tests (create / get / list / patch happy + error paths).
- [x] `pytest.ini`.
- [x] Docker compose: env passthrough (`ORION_URL`, `FIWARE_SERVICE`, `FIWARE_SERVICEPATH`), `depends_on: orion`, mount `tests/` and `pytest.ini`.
- [x] `.env.example`: add `ORION_URL`, `FIWARE_SERVICE`, `FIWARE_SERVICEPATH`, `API_PREFIX`.
- [x] `Makefile`: add `test` target.
- [x] Run `make up && make test` — 19/19 green.
- [x] Update roadmap.
- [x] Commit + push.
