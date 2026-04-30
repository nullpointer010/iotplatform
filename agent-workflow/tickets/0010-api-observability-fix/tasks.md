# Tasks — Ticket 0010

- [x] Pass `disable_existing_loggers=False` to `fileConfig` in `alembic/env.py`.
- [x] Add `PYTHONUNBUFFERED=1` to the `iot-api` service in `compose/docker-compose.api.yml`.
- [x] New `app/middleware.py` with `RequestIdMiddleware`.
- [x] In `app/main.py`: `logging.basicConfig`, register `RequestIdMiddleware`, register global `Exception` handler that logs via `app.errors` and returns the `{detail, request_id}` envelope.
- [x] New `tests/test_observability.py` covering: envelope + caplog, generated id format, header on success route, malformed incoming id replaced.
- [x] `make test` (live stack) → 80/80 pass.
- [x] Live smoke: `GET /healthz` returns `X-Request-ID`; `docker logs iot-api` shows uvicorn access lines after the access log restoration.
