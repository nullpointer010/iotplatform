# Design — Ticket 0013 (keycloak-and-edge-auth)

## Approach

Add three new services to the existing single-stack compose file
(`platform/compose/docker-compose.base.yml`): `keycloak-db`, `keycloak`,
and `oauth2-proxy`. All three are bound to `127.0.0.1` only. The web
UI keeps running as `npm run dev` on the host; `oauth2-proxy` reaches
it via `host.docker.internal` (with `extra_hosts: host-gateway` for
Linux portability).

Realm is provisioned by Keycloak's built-in `--import-realm` from a
hand-written, committed `platform/config/keycloak/realm-iot.json`.
Realm: `iot-platform`. Roles: `viewer`, `operator`,
`maintenance_manager`, `admin`. Two clients: `iot-web` (confidential,
dev secret committed in the realm JSON, used by oauth2-proxy) and
`iot-api` (confidential, dev secret committed; reserved for ticket
0014). Four seed users — `viewer`, `operator`, `manager`, `admin` —
with password `change-me-<role>` and the matching role attached.

`oauth2-proxy` is configured via env vars on the compose service (one
file is enough; no separate `oauth2-proxy.cfg`). Cookie secret comes
from `OAUTH2_PROXY_COOKIE_SECRET` in `.env` (gitignored). A new Make
target `make secrets-keycloak` prints copy-paste commands to generate
the cookie secret — the command is not auto-executed so the developer
controls when secrets are written.

Locking down `:3000` is explicitly deferred. After 0013, `:3000` is
still wide open; `:4180` is the authenticated entry point. 0014/0015
will add backend RBAC and role-aware UI. We document this in
`journal.md`.

## Alternatives considered

- **A) Single compose file (chosen)** — matches the "auth is always
  present once 0013 lands" decision. One `make up`, one stack.
- **B) Separate `docker-compose.auth.yml` toggled by `make up-with-auth`**
  — rejected: doubles the matrix of "states the dev environment can
  be in" and contradicts the spec. Worse for new contributors.
- **C) Public `iot-web` client with empty secret** — rejected:
  oauth2-proxy historically refuses empty client secrets and requires
  workarounds (`--client-secret=secret` placeholder). Confidential
  client with a dev-only secret committed to the realm JSON is the
  least-friction path.
- **D) Dockerise `npm run dev` in this ticket** — rejected: out of
  scope, would bloat 0013. `host.docker.internal` is enough for dev.
- **E) Use `keycloak-config-cli` or Terraform for the realm** —
  rejected: hand-written JSON is small, reviewable, and Keycloak's
  built-in `--import-realm` covers it.

## Affected files / new files

**New**
- `platform/config/keycloak/realm-iot.json` — realm export with the 4
  roles, 2 clients (`iot-web`, `iot-api`), 4 seed users with
  pre-hashed passwords. Hand-written; tokens lifespans set for dev
  (access 1800s, refresh 3600s).

**Modified**
- `platform/compose/docker-compose.base.yml` — add `keycloak-db`,
  `keycloak`, `oauth2-proxy` services and a `keycloak_db_data`
  volume.
- `platform/.env.example` — add the new variables (see *Data /
  contract* below). Real `platform/.env` updated locally; not
  committed.
- `Makefile` — add `secrets-keycloak`, `logs-keycloak`,
  `logs-oauth2-proxy` targets.
- `.gitignore` — already covers `platform/.env`; no change expected.

## Data model / API contract changes

No app-level API change. New env contract in `platform/.env(.example)`:

```
# Keycloak admin
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=change-me-admin

# Keycloak DB (separate from the iot-platform Postgres)
KEYCLOAK_DB_USER=keycloak
KEYCLOAK_DB_PASSWORD=change-me-kcdb
KEYCLOAK_DB_NAME=keycloak

# Host port for Keycloak (8080 is often busy)
KEYCLOAK_HTTP_PORT=8081

# oauth2-proxy
OAUTH2_PROXY_PORT=4180
OAUTH2_PROXY_CLIENT_ID=iot-web
OAUTH2_PROXY_CLIENT_SECRET=dev-iot-web-secret
# 32-byte base64; generate with: openssl rand -base64 32 | tr -- '+/' '-_' | tr -d '='
OAUTH2_PROXY_COOKIE_SECRET=
# Where the host-side `npm run dev` listens
OAUTH2_PROXY_UPSTREAM=http://host.docker.internal:3000
```

`OAUTH2_PROXY_CLIENT_SECRET` matches the secret baked into
`realm-iot.json` for the `iot-web` client. Both are dev-only.

## Risks

- **Realm JSON drift.** If the import file falls out of sync with what
  Keycloak expects, the container fails on start.
  → Validate the file by importing into a fresh container before
  committing; commit the *exact* JSON Keycloak emits when adjusting
  via Admin UI in dev. Document the validation step in
  `tasks.md`.
- **Cookie-secret length.** oauth2-proxy refuses cookie secrets that
  are not 16/24/32 bytes.
  → `secrets-keycloak` target generates exactly 32 base64-decoded
  bytes via `openssl rand -base64 32`.
- **`host.docker.internal` on Linux.** Older Docker builds need the
  `host-gateway` mapping.
  → Add `extra_hosts: ["host.docker.internal:host-gateway"]` on the
  oauth2-proxy service.
- **Issuer mismatch.** Keycloak inside Docker is reached at
  `http://keycloak:8080`, but the browser is redirected to
  `http://localhost:8081`. This is a known oauth2-proxy /
  Keycloak combo footgun — token issuer claim must match what the
  proxy validates against.
  → Use `--oidc-issuer-url=http://localhost:8081/realms/iot-platform`
  AND set Keycloak `KC_HOSTNAME_URL=http://localhost:8081` so emitted
  tokens carry the same issuer. oauth2-proxy can talk to
  `http://keycloak:8080` for `--login-url` etc., but the *issuer*
  must be the externally-visible URL. Document in `journal.md`.
- **Port collisions.** Keycloak on 8081, oauth2-proxy on 4180; the
  existing FIWARE / API / web ports are 1026, 8000, 3000. No
  collisions. Postgres for Keycloak is internal-only (no host port
  publish) so it cannot clash with the existing `postgres` service.
- **Secrets in git.** `realm-iot.json` will contain a dev-only client
  secret in plaintext. This is acceptable because the realm is local
  dev only and prod will get a separate provisioning path; we mark
  the file with a comment-equivalent note in `tasks.md` and the
  ticket review.

## Test strategy for this ticket

- **No unit tests added.** This ticket is infrastructure config; the
  unit-testable pieces (JWT validation, RBAC) are 0014.
- **Integration / smoke (manual, scripted in `tasks.md`):**
  1. `make down -v` (clean state) → `cp platform/.env.example platform/.env`
     → fill `OAUTH2_PROXY_COOKIE_SECRET` via `make secrets-keycloak`
     instructions.
  2. `make up`. Wait for `keycloak` healthcheck.
  3. `curl -fsS http://localhost:8081/realms/iot-platform/.well-known/openid-configuration | jq .issuer`
     → expect `http://localhost:8081/realms/iot-platform`.
  4. Open `http://localhost:8081/realms/iot-platform/account/`,
     log in as `viewer / change-me-viewer`. Expect success.
  5. Start `cd web && npm run dev`. Open
     `http://localhost:4180/devices` in a clean browser session.
     Expect redirect to Keycloak. Log in as `admin /
     change-me-admin`. Expect the existing devices page.
  6. `curl -I http://localhost:4180/devices` (no cookie) → expect
     `302` to Keycloak.
  7. `http://localhost:4180/oauth2/sign_out` clears the session;
     repeating step 5 redirects again.
  8. Existing automated suites untouched: `make test`,
     `cd web && npm test`, `npx tsc --noEmit`, `npx next build` all
     stay green.
