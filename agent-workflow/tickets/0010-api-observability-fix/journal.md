# Journal — Ticket 0010

## 2026-04-30 — Implementation

### Diagnosis (carried over from 0009)
While running `make seed` in 0009, the seed script reported many
`POST /api/v1/devices -> 500` with no body and no traceback in
`docker logs iot-api`. The container only ever printed the pre-startup
uvicorn banner and Alembic's two `INFO` lines.

Root cause traced to two bugs:
1. `alembic/env.py` calls `logging.config.fileConfig(...)` from inside
   the FastAPI `lifespan` (via `_run_migrations`). `fileConfig`
   defaults to `disable_existing_loggers=True`, so it disables every
   logger that already exists at that moment — including
   `uvicorn.access` and `uvicorn.error`. Hence: no access logs after
   startup, ever.
2. `create_app()` had no global `Exception` handler. Starlette's
   default response for an unhandled exception is the literal string
   `Internal Server Error` with no logging.

The combination meant 500s were silently dropped on the floor.

### Implementation
- Flipped `disable_existing_loggers=False` in `env.py`.
- Added `RequestIdMiddleware` (BaseHTTPMiddleware) that reads or mints
  an id, stores it on `request.state`, and echoes it as `X-Request-ID`
  on every response.
- Registered a global `Exception` handler that logs via `app.errors`
  with `logging.exception(...)` (auto-attaches `exc_info`) and returns
  `{"detail": "Internal server error", "request_id": rid}` with the
  same id in the response header.
- One `logging.basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")`
  at the top of `create_app()`. Idempotent; uvicorn keeps its own
  access-log handler.
- `PYTHONUNBUFFERED=1` added to compose for belt-and-suspenders.

### Tests
Existing tests run against the live container, so an in-process
test was added using `fastapi.testclient.TestClient`. It registers a
`/__boom` route that always raises and asserts:
- response is 500 with the JSON envelope and `request_id` echoed in
  body and `X-Request-ID` header;
- `caplog` records a single ERROR on `app.errors` with `exc_info[0]
  is RuntimeError`, the path and the `rid` in the message;
- a missing `X-Request-ID` produces a 12-hex generated id;
- a malformed incoming `X-Request-ID` (with spaces) is replaced.

`TestClient` is constructed without a context manager so the lifespan
(which would run alembic against postgres) is skipped — these tests
are pure HTTP-contract tests of the middleware + handler combo.

### Verification
- `make test` → 80 passed (4 new + 76 pre-existing).
- `curl -i http://localhost/healthz` → `X-Request-ID` present, access
  log line appears in `docker logs iot-api`.
- `make seed` (still using 0008's old SITES list) ran with full
  visibility into per-request access logs. 0009 is unblocked.

### Lessons
- Calling `fileConfig` outside the very top of process startup is
  almost always wrong. The Alembic-generated `env.py` template
  doesn't pass `disable_existing_loggers=False`; downstream FastAPI
  apps that run migrations from `lifespan` should be aware.
- "Empty 500 with no traceback" is almost always a logging-configuration
  bug, not a route bug. Worth checking before chasing data shape.
