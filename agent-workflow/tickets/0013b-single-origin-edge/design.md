# Design — 0013b single-origin edge

## Topology

```
                ┌────────────────────────────────────────────────┐
   browser ──►  │ 127.0.0.1:80  oauth2-proxy (front door, login) │
                │   ├─ /api/*  → http://api:8000          (iot-net)
                │   └─ /*      → http://host.docker.internal:3000
                └────────────────────────────────────────────────┘
                        ▲                       ▲
                        │ redirect              │ JWKS / token exchange
                        │                       │
                ┌─────────────────┐   ┌──────────────────────┐
                │ 127.0.0.1:8081  │◄──┤ Keycloak (iot-net)    │
                │ Keycloak (host) │   └──────────────────────┘
                └─────────────────┘

  iot-api: NO host port. Only `iot-net`. Reachable from oauth2-proxy
           and from sibling containers as `http://api:8000`.
```

## Compose changes (`platform/compose/docker-compose.api.yml`)

- Remove the `ports:` block from the `api` service. Keep `expose: ["8000"]`
  (or omit; it's the same on `iot-net`).

## Compose changes (`platform/compose/docker-compose.base.yml`)

oauth2-proxy:
- `ports: 127.0.0.1:80:4180` (was `${OAUTH2_PROXY_PORT}:4180`).
- `OAUTH2_PROXY_REDIRECT_URL: http://localhost/oauth2/callback`
- `OAUTH2_PROXY_UPSTREAMS: http://api:8000/api/,http://host.docker.internal:3000/`
  (order matters — first prefix wins; `/api/` first so Next.js can never shadow it).
- depends_on now includes `api: { condition: service_started }`.
- Keep `OAUTH2_PROXY_OIDC_AUDIENCE_CLAIMS: azp` (carry-over from the post-0013 hot-fix).

## Realm changes (`platform/config/keycloak/realm-iot.json`)

`iot-web` client:
- `redirectUris`: `["http://localhost/oauth2/callback"]` (was `:4180`).
- `webOrigins`:   `["http://localhost"]`.

This requires re-importing the realm. Two options:
1. `docker compose down -v` (nukes the keycloak-db volume, fresh import). Simple.
2. Use kcadm to update in-place. More moving parts, no benefit in dev.

**Choice**: drop the keycloak-db volume on `make up` for this ticket. Document
in the journal that local Keycloak edits made via the admin UI are wiped by
`down -v`; that's acceptable for dev where the realm is repo-managed.

## API changes

- `platform/api/app/config.py`: change default `cors_allow_origins` from
  `"http://localhost:3000"` to `""` (empty allow-list — same-origin doesn't
  need it, but the middleware stays loaded as a safety net).
- `main.py:60`: when `origins == []`, the middleware is added with an empty
  list, which means no cross-origin request is allowed. That's the desired
  default. No code change needed in `main.py`.

## Web changes

- `web/.env.local.example`: `NEXT_PUBLIC_API_BASE_URL=` (empty → `fetch("/api/v1/...")`
  is same-origin relative).
- `web/src/lib/api.ts`: change `BASE` default from `"http://localhost"` to
  `""`. Resulting fetch URL becomes `/api/v1/...` — relative, same-origin.
- Local `web/.env.local` to be updated by the user; the example is the contract.

## Env

- `platform/.env.example`: drop `API_PORT` (no longer relevant for browser
  traffic). Drop `OAUTH2_PROXY_PORT` (always `80` now). Note in a comment
  that the API has no host port; access it via `docker exec` or
  `docker compose port api 8000` for debugging.
- `platform/.env`: same edits.

## Make

No new targets. `logs-oauth2-proxy` and `logs-keycloak` already exist.

## Risks

- **Port 80 already in use on the dev host** (Apache, nginx, …). Mitigation:
  document `ss -tlnp 'sport = :80'` in the journal. If a conflict exists,
  the user can override with `OAUTH2_PROXY_HOST_PORT` (we'll keep one knob
  for that case — see open question 2 was "only :80", but a single override
  variable for port collisions is harmless).
  *Decision*: keep a `WEB_PORT` variable defaulting to `80`. One knob, no
  separate `:4180` exposure.
- **oauth2-proxy upstream prefix matching**: requests to `/api/v1/devices`
  must not reach Next.js. With upstreams ordered `/api/` then `/`, oauth2-proxy
  longest-prefix-matches; `/api/v1/devices` → api:8000. Verified by the AC.
- **Keycloak admin UI** (at `http://localhost:8081/admin`) is still exposed
  on the host and unprotected by oauth2-proxy. Acceptable for dev; flagged
  as a follow-up for the production hardening ticket.
