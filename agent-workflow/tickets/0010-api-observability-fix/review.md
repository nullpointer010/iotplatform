# Review — Ticket 0010 — api-observability-fix

## Self-review (agent)

### Acceptance criteria
- [x] `GET /healthz` produces a uvicorn access log line in
      `docker logs iot-api`. **Verified live.**
- [x] Unhandled exception → 500 with
      `{"detail":"...", "request_id":"..."}` JSON body and matching
      `X-Request-ID` header. **Verified by `test_observability.py`.**
- [x] Migrations still run on startup; uvicorn loggers no longer
      disabled. **Verified live: `Will assume transactional DDL.`
      followed by access logs.**
- [x] `PYTHONUNBUFFERED=1` set on `iot-api`. **In compose.**
- [x] Pytest case asserts envelope shape + `caplog` capturing
      `exc_info=RuntimeError`. **`test_observability.py`.**
- [x] All 80 tests green (`make test`).
- [x] `make seed` is unblocked: any future 500 will now leave a
      traceback. (Resuming 0009 next.)

### Files changed
- `platform/api/alembic/env.py` — `disable_existing_loggers=False`.
- `platform/api/app/main.py` — basicConfig, middleware registration,
  global `Exception` handler.
- `platform/api/app/middleware.py` — new, ~30 lines.
- `platform/api/tests/test_observability.py` — new, 4 cases.
- `platform/compose/docker-compose.api.yml` — `PYTHONUNBUFFERED=1`.

No production routes were modified. No new dependencies.

### Notes / follow-ups
- Structured-JSON logging, OTel, Prometheus deferred to a Phase 2
  observability ticket.
- Worth distilling into `agent-workflow/memory/gotchas.md` after this
  closes:
  *"Calling `logging.config.fileConfig` from inside FastAPI `lifespan`
  silently disables every uvicorn logger; pass
  `disable_existing_loggers=False` or move it to import time."*

## External review (Codex / human)
<empty — awaiting reviewer>
