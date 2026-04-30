# Tasks — 0004 telemetry-and-state

- [x] Add `quantumleap_url` to `app/config.py`.
- [x] `app/quantumleap.py`: async `QuantumLeapClient.query_entity` with 200/404 handling.
- [x] `app/deps.py`: add `QuantumLeapDep`.
- [x] `app/schemas_telemetry.py`: `TelemetryEntry`, `TelemetryResponse`, `StateResponse` (forbid extras).
- [x] `app/routes/telemetry.py`: `GET /devices/{id}/telemetry` (QL-backed), `GET /devices/{id}/state` (Orion-backed projection).
- [x] Wire QL client + telemetry router in `app/main.py`.
- [x] `.env.example`: `QUANTUMLEAP_URL`.
- [x] `docker-compose.api.yml`: env passthrough + `depends_on: quantumleap`.
- [x] Extend `tests/conftest.py` with `ql` fixture, `push_measurement`, `wait_for_ql`.
- [x] `tests/test_telemetry.py`: 11 behaviour tests (telemetry happy + error paths, state subset).
- [x] Fix `setup_orion_subscription.sh` to be properly idempotent (delete duplicate subscriptions instead of skipping when one already exists).
- [x] Run `make up && make test` — 30/30 green.
- [x] Update roadmap.
- [x] Commit + push.
