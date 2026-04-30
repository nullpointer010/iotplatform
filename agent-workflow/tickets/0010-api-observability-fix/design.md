# Ticket 0010 — Design

## Approach
Three small, surgical changes plus one test. Each addresses one
distinct symptom of the observability failure.

### 1. Stop Alembic from disabling uvicorn loggers
[`platform/api/alembic/env.py`](../../../platform/api/alembic/env.py)
calls `fileConfig(config.config_file_name)` unconditionally. The
default of `disable_existing_loggers=True` is the cause. Pass
`disable_existing_loggers=False` so `uvicorn.access` and
`uvicorn.error` (created before the lifespan hook) survive.

This also keeps Alembic's own log behaviour unchanged, since the
`alembic.ini` `[loggers]` section is still applied.

### 2. Configure root logging once, at app construction time
Today nothing calls `logging.basicConfig`, so application-level
loggers (any future `logging.getLogger(__name__)`) print nothing in
the container. Add a single one-liner at the top of `create_app()`:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
```

Rationale: idempotent (basicConfig is a no-op if root already has a
handler — which uvicorn doesn't add), affects only our app's
loggers, leaves uvicorn's own access-log format alone (uvicorn
configures `uvicorn.access` directly with its own handler, so our
root handler isn't duplicated). Verified by reading
`uvicorn.config.LOGGING_CONFIG`.

### 3. Add a global Exception handler with request_id
In `create_app()`, after middleware:

```python
@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    rid = request.state.request_id  # set by middleware below
    logging.getLogger("app.errors").exception(
        "Unhandled error %s %s rid=%s", request.method, request.url.path, rid,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": rid},
        headers={"X-Request-ID": rid},
    )
```

Note: FastAPI/Starlette will not call this handler for `HTTPException`
(those have their own handler) — exactly what the requirements ask
for. `logging.exception` automatically captures `exc_info`.

### 4. request_id middleware
A lightweight ASGI middleware that, for every request:
- reads the incoming `X-Request-ID` header if present and well-formed
  (a-z0-9-_ up to 64 chars), else generates `uuid4().hex[:12]`;
- stores it on `request.state.request_id`;
- adds the same value as `X-Request-ID` on the outgoing response.

Implemented as a `BaseHTTPMiddleware` subclass — small enough that the
extra middleware-stack hop is fine, and it lets us mutate the response
headers cleanly. Lives in a new file
`platform/api/app/middleware.py` (~30 lines).

### 5. PYTHONUNBUFFERED in compose
Add `PYTHONUNBUFFERED=1` to the `iot-api` service in
[`platform/compose/docker-compose.api.yml`](../../../platform/compose/docker-compose.api.yml).
Belt-and-suspenders: with uvicorn writing to stdout (a pipe in
Docker), Python is line-buffered by default, but explicit beats
implicit and shields us from any future change that re-attaches a
non-tty fd.

## Why this and not more
- **Not a custom JSON-logging library**: standard `logging` is enough
  for v1; structured logs are a Phase 2 ticket alongside Prometheus.
- **Not a full request/response audit middleware**: out of scope per
  requirements; a 30-line request_id middleware doesn't introduce a
  new abstraction we'd regret.
- **Not changing `alembic.ini` to a Python dictconfig**: the keyword
  flip in `env.py` already solves it; rewriting the ini would be a
  ten-line diff for zero behavioural gain.
- **Not adding a `/api/v1/me` or any ops endpoint**: belongs in the
  auth tickets.

## Files touched
| File | Change |
|---|---|
| `platform/api/alembic/env.py` | `fileConfig(..., disable_existing_loggers=False)` |
| `platform/api/app/main.py` | `logging.basicConfig`, register middleware, register exception handler |
| `platform/api/app/middleware.py` (new) | `RequestIdMiddleware` |
| `platform/api/tests/test_observability.py` (new) | error envelope + caplog test |
| `platform/compose/docker-compose.api.yml` | `PYTHONUNBUFFERED=1` |

That is the entire surface area. No route file is modified, no
existing test changes.

## Test plan

### New pytest case
`tests/test_observability.py`:

1. Use FastAPI dependency override or a tiny test-only route added via
   `app.add_api_route("/__boom", lambda: (_ for _ in ()).throw(RuntimeError("boom")))`
   inside the test fixture (the cleanest way; no production code
   pollution).
2. Hit `GET /__boom` with `X-Request-ID: testrid123`. Assert:
   - status 500;
   - JSON body `{"detail": "Internal server error", "request_id": "testrid123"}`;
   - response header `X-Request-ID == "testrid123"`.
3. With `caplog.at_level(logging.ERROR)` capturing `app.errors`:
   - exactly one record;
   - `record.exc_info[0] is RuntimeError`;
   - `"rid=testrid123"` in `record.getMessage()`.
4. Second request without `X-Request-ID`: assert response header
   matches `^[a-f0-9]{12}$`.

### Smoke
- `make test` → all existing + new tests pass.
- `make up && curl -i http://localhost/api/v1/devices` → access log
  line in `docker logs iot-api`, `X-Request-ID` header present.
- `make seed` → fails or succeeds, but the next failing 500 in 0009
  produces a real traceback. (Confirms 0009 is unblocked.)

## Risks
- **basicConfig double-handler.** Mitigated by basicConfig being a
  no-op if root has handlers; we are the first to call it.
- **BaseHTTPMiddleware perf.** Documented Starlette caveat (extra task
  group). Acceptable for v1 — a hundreds-of-rps platform doesn't run
  on a `--reload` dev image anyway, and Phase 2 can switch to a pure
  ASGI middleware if needed.
- **Existing tests breaking.** None of them assert on response
  headers, body shape of 500s, or log capture. Adding `X-Request-ID`
  on every response and a JSON envelope only on 500s is additive.
- **Alembic running on every reload.** Existing behaviour, unchanged.

## Out of scope (re-stated)
Sentry, OTel, Prometheus, structured-JSON logging, per-route timing
middleware, response-size metering, alembic.ini rewrite. Resuming
0009 is *enabled* by this ticket but happens after it closes.
