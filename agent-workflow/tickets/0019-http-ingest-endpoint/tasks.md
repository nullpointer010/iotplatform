# Tasks — Ticket 0019

- [x] T1 Create `app/ingest.py` with `upsert_measurement` and
      `apply_measurement` (extracted from MqttBridge).
- [x] T2 Refactor `MqttBridge._forward` to delegate; remove
      `_upsert_measurement`.
- [x] T3 Add Alembic migration `0004_device_ingest_keys.py` and
      model `models_ingest_keys.py`. Register import in
      `alembic/env.py`.
- [x] T4 Add `device_ingest_keys` to `pg_clean` TRUNCATE in
      `tests/conftest.py`.
- [x] T5 Add `app/schemas_ingest.py`.
- [x] T6 Add `app/routes/ingest.py`; wire in `main.py`. Bonus:
      delete_device also drops the ingest key row (mirrors
      maintenance log cleanup).
- [x] T7 Write `tests/test_http_ingest.py` (12 tests).
- [x] T8 `make test` — 182 passed, 1 pre-existing flake
      (`test_query_lastN_limits_results`). New: 12 ingest tests +
      10 mqtt bridge tests still green.
- [x] T9 Updated `architecture.md` (Ingestion + Routes) and
      `agent-workflow/memory/gotchas.md` (dual auth ladder).
      Roadmap flipped 0018b + 0019 to done.
- [x] T10 Filled journal/review; flipped status to done; commit.
