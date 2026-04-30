# Self-review — 0013b single-origin edge

## ACs

1. ✓ `iot-api` has no host port (`docker ps` shows only `8000/tcp`).
2. ✓ Unauthenticated `curl http://localhost/api/v1/devices` 302s to Keycloak.
3. ✓ After login the same URL returns JSON; no CORS preflight.
4. ✓ `curl http://localhost:8000` from host fails; `iot-api:8000` works
   from sibling containers on `iot-net`.
5. ✓ `make up` clean. Web vitest 2/2, tsc clean, next build 7/7.
   API 79/80 (1 pre-existing flake, not introduced by this ticket).
6. ✓ Realm `iot-web.redirectUris = ["http://localhost/oauth2/callback"]`,
   `webOrigins = ["http://localhost"]`.
7. ✓ `web/.env.local.example`, `platform/.env.example` updated with
   topology comments. `WEB_PORT=80` default; `API_PORT` removed.

## Risks / follow-ups

- Keycloak admin UI on `:8081` is unprotected; acceptable for dev,
  flagged for prod-hardening ticket (≥0016).
- Pre-existing telemetry race-condition flake should get its own ticket.
- `WEB_PORT` override is wired but the realm redirect URIs are hard-coded
  to `http://localhost/...`. If a dev sets `WEB_PORT=8080` they must add
  `http://localhost:8080/oauth2/callback` to the realm and update the
  proxy's `OAUTH2_PROXY_REDIRECT_URL`. Documented in journal.

## Security

- Backend is now unreachable from the host network. Only routes that
  pass through oauth2-proxy can hit it. Auth enforcement on the bearer
  itself is still 0014's job.
- CORS allow-list flipped to empty by default (same-origin doesn't need
  it; middleware loaded as a safety net).

## Diff scope

- `platform/compose/docker-compose.api.yml` — drop `ports`, add `expose`.
- `platform/compose/docker-compose.base.yml` — oauth2-proxy port → 80,
  upstreams → api+web, redirect URL hard-coded, depends_on api.
- `platform/config/keycloak/realm-iot.json` — redirect/origins to `http://localhost`.
- `platform/.env.example`, `platform/.env` — drop API_PORT/OAUTH2_PROXY_PORT/
  OAUTH2_PROXY_UPSTREAM, add WEB_PORT.
- `platform/api/app/config.py` — CORS default `""`.
- `web/.env.local.example`, `web/.env.local` — empty `NEXT_PUBLIC_API_BASE_URL`.
- `web/src/lib/api.ts` — `BASE` default `""`.
- Ticket files (requirements/design/tasks/journal/review/status).
- `agent-workflow/roadmap.md` — append 0013b entry.
