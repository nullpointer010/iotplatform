# Ticket 0013 — keycloak-and-edge-auth

## Problem
The web app and the FastAPI backend are unauthenticated: anyone with
network access to `localhost:3000` or `localhost:8000` can read and write
every device, telemetry stream and maintenance log. The product spec
(`context/doc/backend.md`) references Keycloak users and four realm
roles (`viewer`, `operator`, `maintenance_manager`, `admin`) but the
identity provider does not exist yet. We need the auth substrate in
place before backend RBAC (0014) and role-aware UI (0015) can be built.

## Goal
Stand up Keycloak 24 + a dedicated `keycloak-db` (postgres 17), import a
realm `iot-platform` with the four spec roles and one seed user per
role, and put `oauth2-proxy` in front of the Next.js dev server so the
web app is reachable only after a successful Keycloak login. Local dev
only — no TLS, no custom hostnames, everything bound to `localhost`.
**The web UI itself does not change** in this ticket; behaviour
(role gating, identity display) lands in 0014/0015.

## User stories
- As a developer, I want `make up` to bring up Keycloak, `keycloak-db`
  and `oauth2-proxy` alongside the existing stack so I can iterate
  without extra commands.
- As a developer, I want a single command (e.g. `make seed-keycloak`
  or just `--import-realm` on container start) to load the realm + users
  so a fresh checkout has working logins out of the box.
- As any test user (`viewer`, `operator`, `maintenance_manager`,
  `admin`), I want to log in at `http://localhost:4180/...` and reach
  the existing Next.js UI; logging out invalidates the session.
- As an operator, I do not want the FastAPI backend exposed to the
  open internet — for v1 it stays on `localhost:8000` and the browser
  reaches it through the Next.js app's existing `/api` proxy
  (unchanged); the JWT enforcement on FastAPI is 0014's concern.

## Acceptance criteria (verifiable)

### Infrastructure
- [ ] `platform/compose/docker-compose.base.yml` (or a dedicated
  `docker-compose.auth.yml` included from the Makefile) defines:
  - `keycloak-db` — `postgres:17` image, named volume, `POSTGRES_DB`
    / `POSTGRES_USER` / `POSTGRES_PASSWORD` from `.env`, **separate
    from the existing `postgres` service** (no shared schema).
  - `keycloak` — `quay.io/keycloak/keycloak:24.0.4`,
    `command: start-dev --import-realm`, mounts
    `platform/config/keycloak/` read-only as
    `/opt/keycloak/data/import`, depends on `keycloak-db` healthcheck,
    bound to `127.0.0.1:8081:8080` (8080 is taken on the host).
  - `oauth2-proxy` —
    `quay.io/oauth2-proxy/oauth2-proxy:v7.6.0` (or newer pinned),
    bound to `127.0.0.1:4180:4180`, configured for the Keycloak OIDC
    provider, `--upstreams=http://host.docker.internal:3000` (so it
    proxies the existing `npm run dev` Next.js process; no need to
    Dockerise the web app yet).
- [ ] `make up` brings up the new services; `make down` tears them
  down; `make logs-keycloak`, `make logs-oauth2-proxy` follow logs.

### Realm + users
- [ ] `platform/config/keycloak/realm-iot.json` defines:
  - Realm name `iot-platform`.
  - Four realm roles: `viewer`, `operator`, `maintenance_manager`,
    `admin`.
  - Public OIDC client `iot-web` with redirect URI
    `http://localhost:4180/oauth2/callback` and web origin
    `http://localhost:4180`.
  - Confidential OIDC client `iot-api` (used later by 0014; created
    here so 0014 can land without re-importing).
  - Four seed users — `viewer`, `operator`, `manager`, `admin` — each
    with password `change-me-<role>`, the matching realm role
    assigned, and email verified.
  - `accessTokenLifespan` reasonable for dev (e.g. 30 min).
- [ ] On a clean `make up`, the realm imports successfully:
  `curl -s http://localhost:8081/realms/iot-platform/.well-known/openid-configuration`
  returns 200 with `issuer == http://localhost:8081/realms/iot-platform`.
- [ ] All four users can log in via the Keycloak account UI at
  `http://localhost:8081/realms/iot-platform/account/`.

### Edge auth (oauth2-proxy)
- [ ] `oauth2-proxy` config (env vars or `oauth2-proxy.cfg`) covers:
  - `--provider=keycloak-oidc`
  - `--oidc-issuer-url=http://keycloak:8080/realms/iot-platform`
    (in-network) — and the published external URL via `redirect_url`.
  - `--client-id=iot-web`, `--client-secret=` empty (public client)
    *or* a dummy value if oauth2-proxy refuses empty; document choice
    in `journal.md`.
  - `--cookie-secret` — 32-byte base64 generated at provisioning,
    persisted in `.env` (gitignored).
  - `--email-domain=*` (Keycloak supplies emails of the seed users).
  - `--pass-access-token=true`, `--pass-authorization-header=true`,
    `--set-xauthrequest=true` so 0015 can read
    `X-Auth-Request-User` / `X-Auth-Request-Email` /
    `X-Auth-Request-Groups` and 0014 can read the bearer token.
  - `--skip-provider-button=false` (prefer the Keycloak login screen
    directly; tweakable).
- [ ] Hitting `http://localhost:4180/devices` while logged out
  redirects to Keycloak; after login, the existing Next.js
  `/devices` page renders unchanged.
- [ ] `http://localhost:4180/oauth2/sign_out` clears the session.
- [ ] The bare Next.js port `http://localhost:3000` keeps working
  unauthenticated for now (oauth2-proxy is additive); a follow-up note
  in `journal.md` records that locking it down is 0014/0015 scope.

### Quality gates
- [ ] No new secrets committed. `.env.example` is updated with
  placeholder values for `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD`,
  `OAUTH2_PROXY_COOKIE_SECRET`, `OAUTH2_PROXY_CLIENT_SECRET` (if
  needed), `KEYCLOAK_DB_USER`, `KEYCLOAK_DB_PASSWORD`. The real
  `.env` stays gitignored.
- [ ] Existing API and web tests still pass: `make test`,
  `cd web && npm test`, `npx tsc --noEmit`, `npx next build`.
- [ ] No FastAPI route is locked yet — locking is 0014.

## Out of scope
- FastAPI JWT validation, JWKS plumbing, `require_roles(*)`
  dependency, RBAC on existing routes — that is **0014**.
- Web UI reading identity / hiding actions per role — that is **0015**.
- HTTPS / Caddy / custom hostnames / production hardening — local dev
  only, all bindings on `127.0.0.1`.
- Swapping Keycloak for an external IdP, federation, social login.
- Realm export / Terraform / Keycloak-config-cli — JSON import is
  enough for now.
- Containerising `npm run dev`. oauth2-proxy uses
  `host.docker.internal` to reach the host-side Next.js process.

## Open questions
1. **Compose file split.** Option A: extend the existing
   `platform/compose/docker-compose.base.yml`. Option B: a new
   `platform/compose/docker-compose.auth.yml` toggled on by
   `make up-with-auth`. Recommendation: A — the spec assumes auth is
   always present once 0013 lands; one stack, one command.
2. **Keycloak host port.** 8080 is commonly busy (and clashes with
   FIWARE Orion on some setups). Recommendation: publish on
   `127.0.0.1:8081` and document the choice in `.env.example`.
3. **`iot-web` client secret.** oauth2-proxy historically dislikes
   empty secrets even for public clients. Recommendation: register
   `iot-web` as **confidential** with a dev-only secret committed to
   `realm-iot.json` (and rotated for prod) — simpler than fighting
   the public-client path.
4. **`oauth2-proxy` cookie secret rotation.** Generated once at
   provisioning and committed to `.env` (gitignored). Recommendation:
   add a `make secrets-keycloak` target that prints commands to
   generate it (does not commit).
5. **Web server reachability from oauth2-proxy.**
   `host.docker.internal` works on Docker Desktop and on Linux
   Docker 20.10+ with `extra_hosts: "host.docker.internal:host-gateway"`.
   Recommendation: declare the `extra_hosts` entry to make it
   portable.
6. **Realm export storage.** Option A: hand-written
   `platform/config/keycloak/realm-iot.json`. Option B: export from a
   running Keycloak the first time. Recommendation: A — small,
   reviewable, deterministic.
