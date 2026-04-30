# Gotchas

Traps and surprises encountered. Append one bullet per gotcha with a link to
the ticket where it bit us.

- Calling `logging.config.fileConfig(...)` from inside FastAPI `lifespan` (e.g. via Alembic's generated `env.py`) silently disables every logger that already exists, including `uvicorn.access` and `uvicorn.error`. Pass `disable_existing_loggers=False` or move it to import time. Symptom: empty 500 responses with no traceback in `docker logs`. (ticket 0010)
- Starlette's default response for an unhandled exception is the literal string `Internal Server Error` with no logging — always register a global `Exception` handler that calls `logging.exception(...)`. (ticket 0010)
- MQTT topic segments reject spaces; never embed a free-form `city` / `site` string into `mqttTopicRoot` without slugifying first. (ticket 0009)
- Orion NGSI v2 forbids the characters `< > " ' = ; ( )` in attribute *values*. Symptom: `400 BadRequest "Invalid characters in attribute value"`. Don't put parentheses, quotes, or semicolons in display strings sent to Orion (e.g. `"Juan Pérez (IFAPA)"` → use `"Juan Pérez - IFAPA"`). The web layer enforces this client-side via `web/src/lib/orion-chars.ts` + `orionSafe()` in `lib/zod.ts`. (ticket 0009, 0011)
- `next-intl` shipped v4 (`^4.11.0`) by default at install time. v4 keeps `useTranslations` / `NextIntlClientProvider` compatible but the official docs default to `i18n/request.ts` + `[locale]` segments — fine to skip if you stay client-side. (ticket 0011)
- When `superRefine`-ing a `ZodString`, downstream helpers like `optionalNonEmpty(s)` must accept `z.ZodTypeAny`, not `z.ZodString` — refinement returns `ZodEffects<ZodString, ...>`. (ticket 0011)
- `tests/test_telemetry.py::test_query_lastN_limits_results` is flaky: depends on QuantumLeap ingestion ordering when 5 measurements arrive within 5 s. Re-run the suite or sort QL output deterministically. (ticket 0011, follow-up FU1)
