# Ticket 0010 — api-observability-fix

## Problem
The FastAPI service silently swallows server-side errors. Concrete
symptoms observed while running `make seed` (during 0009):

- Many `POST /api/v1/devices` calls return `500 Internal Server Error`
  with no body and no traceback anywhere in `docker logs iot-api`.
- No HTTP access log lines are emitted at all after the lifespan
  finishes — only the pre-startup uvicorn banner is visible.

Root cause analysis (see 0009 `journal.md` for the full trail):

1. `platform/api/alembic/env.py` calls `logging.config.fileConfig(...)`
   on `alembic.ini`. `fileConfig` defaults to
   `disable_existing_loggers=True`, which disables every logger
   defined before the call — including `uvicorn.access` and
   `uvicorn.error`.
2. Migrations run inside FastAPI's `lifespan` context manager
   (`app/main.py::_run_migrations`), i.e. **after** uvicorn has
   already created its loggers. So the disable wins.
3. There is no global `Exception` handler in `create_app()`. Any
   non-`HTTPException` raised by a route is converted to
   `500 Internal Server Error` by Starlette with body
   `Internal Server Error` and no log line.

Combined effect: in production this app would handle hundreds of
requests with zero observability into failures. We can't even debug
the seeding 500 that is currently blocking 0009.

This is an app-wide infrastructure bug. It is being raised as its own
ticket so the fix is not silently folded into a data-content ticket
(0009).

## Goal
Every unhandled exception in any FastAPI route is captured in the
container's stdout with a full traceback, and the client receives a
stable JSON error envelope instead of a bare `Internal Server Error`
string. uvicorn access logs flow normally for every request.

## User stories
- As an operator running the platform, I want every 500 to appear in
  `docker logs iot-api` with a stack trace so I can diagnose problems
  without attaching a debugger.
- As a frontend / API client, I want 500 responses to carry a JSON body
  with `detail` so the UI can render a sensible error and so logs
  on the client side correlate with server-side traces.
- As an agent debugging seed failures (0009), I want to see the actual
  exception class + message + traceback the first time it happens.

## Acceptance criteria (verifiable)
- [ ] `make up` followed by any request to a 200-route prints a single
      `INFO  ...  "GET /api/v1/devices HTTP/1.1" 200` line in
      `docker logs iot-api` (uvicorn access log restored).
- [ ] Any route that raises a non-`HTTPException` causes:
      - the response to be `500` with body
        `{"detail": "...", "request_id": "..."}` (JSON, not plain text);
      - a single `ERROR` log line in stdout with the full traceback,
        the request method, the request path, and the same
        `request_id` value.
- [ ] Migrations still run on startup (alembic logs `Will assume
      transactional DDL.`), and uvicorn loggers are NOT disabled by
      that step (no regression on existing behaviour).
- [ ] `PYTHONUNBUFFERED=1` is set on the `iot-api` compose service so
      stdout is line-buffered.
- [ ] A new pytest case asserts that a route raising `RuntimeError`
      yields `500` with the JSON envelope shape, and that
      `caplog.records` contains one ERROR-level record whose `exc_info`
      includes the original `RuntimeError`.
- [ ] All pre-existing pytest cases still pass (`make test`).
- [ ] `make seed` against a clean stack runs to *some* result and any
      remaining 500 now leaves a real traceback in
      `docker logs iot-api` (this is what unblocks 0009).

## Out of scope
- Sentry / OpenTelemetry / structured-JSON logging libraries. We use
  the standard `logging` module only.
- Per-request middleware that times every request, response-size
  metering, Prometheus metrics — all later observability tickets if
  needed.
- Rewriting `alembic.ini` to a Python-dictconfig. Minimal flag flip is
  enough.
- Any change to seed data or to the 0009 scope. 0009 stays paused;
  resumed only after this ticket closes.

## Open questions
- **Where to generate `request_id`?** Default plan: pull from incoming
  `X-Request-ID` header if present, otherwise `uuid4().hex[:12]`.
  Echoed back in the response header `X-Request-ID` and in the log
  line. OK?
- **Should `HTTPException` responses also gain `request_id`?** Default:
  yes — same middleware sets the header on every response, but only
  the unhandled-exception branch logs and only that branch puts the id
  in the body (HTTPExceptions already carry a meaningful `detail`).
- **Log format**: stick with uvicorn's default `INFO:` text format, or
  switch to a richer one (timestamp + level + name)? Default: configure
  the root logger with `%(asctime)s %(levelname)s %(name)s %(message)s`
  so application logs are timestamped, and leave uvicorn's own access
  format alone.
