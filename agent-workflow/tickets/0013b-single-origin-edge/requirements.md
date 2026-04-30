# 0013b — Single-origin edge

## Problem

After 0013 the dev stack has **two browser-facing origins**:

- `http://localhost:4180` — oauth2-proxy → Next.js (login)
- `http://localhost`      — FastAPI (data)

Consequences:

1. Browser blocks API calls from the web UI (CORS allow-list was `:3000` only).
2. The API is reachable on the host without authentication. Anyone on the
   loopback (or any container that exposes a host port mapping) can hit it.
3. In 0014 the web has to hand-craft a way to attach the Keycloak bearer
   token to a different origin than the one it loaded from. Annoying and
   un-prod-like.

The user's desired shape: **the API must not be on `:80`. It should only
be reachable internally. The web (via the auth proxy) should own `:80`.**

## Goal

One front door: `http://localhost`. Behind it:

```
localhost:80 ──► oauth2-proxy
                 ├─ /api/*  ──► iot-api  (container, no host port)
                 └─ /*      ──► Next.js dev (host.docker.internal:3000)
```

Result: same-origin, no CORS, API not exposed to the host network.

## Acceptance criteria

1. `docker ps` shows **no host-port mapping** for `iot-api`. The container
   listens only on `iot-net` (port `8000` internal).
2. `curl -I http://localhost:80/api/v1/devices` issued from a browser
   without a session is **redirected to Keycloak** (not answered by the API).
3. After login, the browser hits `http://localhost/api/v1/devices` and
   receives JSON. No CORS preflight is required (same-origin).
4. `curl -I http://localhost:8000/...` from the host **fails** (port not
   bound). `curl` from inside another container on `iot-net` to
   `http://api:8000/...` still works (internal traffic preserved).
5. `make up` brings the stack up cleanly. `make test` and `cd web && npm test`
   stay green.
6. Keycloak `iot-web` client redirect URI updated to `http://localhost/oauth2/callback`.
   Old `:4180` redirect URI removed.
7. `web/.env.local.example` and `platform/.env.example` updated; comments
   explain the new topology in two sentences.

## Out of scope

- Bearer-token enforcement on the API (that is 0014).
- TLS / production hostnames.
- Replacing oauth2-proxy with Caddy/nginx (revisit when we add HTTPS).

## Open questions

1. **Drop `API_PORT` from `.env` entirely**, or keep it as an opt-in for
   developers who want direct host access while debugging?
   *Recommended: drop it. Direct host access defeats the point of this ticket.
   Devs can still `docker exec` or `docker compose port` if they need it.*

2. **Should oauth2-proxy continue to expose `:4180` on the host as well**,
   or only `:80`?
   *Recommended: only `:80`. One front door.*

3. **CORS in FastAPI**: leave the middleware loaded with an empty allow-list,
   or remove the middleware entirely?
   *Recommended: leave the middleware, set the allow-list to empty by default.
   Same-origin requests don't trigger it; it stays as a safety net for any
   future cross-origin tooling.*

4. **`OAUTH2_PROXY_UPSTREAMS` ordering**: put `/api/` first so Next.js can
   never shadow it. Confirm.
   *Recommended: yes. `/api/` first, `/` last.*

5. **Next.js dev server**: keep on host (`host.docker.internal:3000`) or
   move into a compose service?
   *Recommended: keep on host. Hot-reload on a bind mount inside Docker is
   slow on Linux and that is a separate concern.*
