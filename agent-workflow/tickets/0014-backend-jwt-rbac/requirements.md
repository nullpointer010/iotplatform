# 0014 — Backend JWT + RBAC

## Problem

After 0013 / 0013b, oauth2-proxy attaches a Bearer token to every
request that reaches FastAPI. The API ignores it. Anyone (or anything)
that can hop onto `iot-net` and reach `http://iot-api:8000` gets
unauthenticated access. RBAC roles (`viewer`, `operator`,
`maintenance_manager`, `admin`) defined in the realm have no effect.

Closes the v1 spec from `context/doc/backend.md` and unblocks 0015
(role-aware UI).

## Goal

1. Every API route validates the incoming JWT against Keycloak's JWKS.
   No token, expired token, wrong issuer/audience → `401`.
2. Each route declares the roles it needs via a `require_roles(*roles)`
   dependency. Token has none of those roles → `403`. Has one → `200`.
3. The realm's 4 seed users (`viewer`, `operator`, `manager`, `admin`)
   exercise the matrix in tests.

## Acceptance criteria

1. Hitting any data route without a token returns `401`.
2. Hitting it with a `viewer` token where `operator` is required returns `403`.
3. Hitting it with the right role returns `200`.
4. `/api/v1/healthz` stays public (liveness probe; oauth2-proxy doesn't
   forward to it but other tooling may).
5. Tokens are validated against Keycloak's JWKS, with caching, and a
   key rotation does not require an API restart.
6. Test suite covers 401 / 403 / 200 on **one representative endpoint
   per resource** (devices, telemetry, state, maintenance/operation-types,
   maintenance/log).
7. `make test` stays green; existing tests get a token-fixture wrapper
   so they continue to pass without per-test boilerplate.
8. The web (now same-origin behind oauth2-proxy) keeps working: the
   proxy already attaches `Authorization: Bearer …` (we set
   `PASS_AUTHORIZATION_HEADER=true` in 0013).

## Role → endpoint matrix

Per `backend.md` and the charter:

| Resource                                | viewer | operator | maintenance_manager | admin |
| --------------------------------------- | :----: | :------: | :-----------------: | :---: |
| `GET    /devices`, `/devices/{id}`      |   ✓    |    ✓     |          ✓          |   ✓   |
| `POST   /devices`                       |        |    ✓     |                     |   ✓   |
| `PATCH  /devices/{id}`                  |        |    ✓     |                     |   ✓   |
| `DELETE /devices/{id}`                  |        |          |                     |   ✓   |
| `GET    /devices/{id}/telemetry|state`  |   ✓    |    ✓     |          ✓          |   ✓   |
| `GET    /maintenance/operation-types`   |   ✓    |    ✓     |          ✓          |   ✓   |
| `POST/PATCH/DELETE /…/operation-types`  |        |          |          ✓          |   ✓   |
| `GET    /maintenance/log…`              |   ✓    |    ✓     |          ✓          |   ✓   |
| `POST/PATCH /…/log…`                    |        |    ✓     |          ✓          |   ✓   |
| `DELETE /…/log/{id}`                    |        |          |          ✓          |   ✓   |
| `GET    /healthz`                       |  public (no auth)                    |

`admin` is implicitly allowed everywhere — implemented as: any of the
required roles **or** `admin`.

## Out of scope

- Per-tenant scoping (FIWARE service header per user). Single tenant in v1.
- Token introspection or refresh on the API side; oauth2-proxy owns
  refresh. The API only validates the access token it receives.
- UI role-awareness; that is 0015.
- Service-to-service auth (machine clients hitting the API directly).

## Open questions

1. **Library**: `python-jose[cryptography]` vs `pyjwt[crypto]` vs
   `authlib`. *Recommended: `pyjwt[crypto]` — smaller surface, actively
   maintained, no transitive deprecation issues that `python-jose` has.*

2. **JWKS caching**: roll our own with `httpx` + an in-memory dict, or
   pull `pyjwt`'s `PyJWKClient` (which caches transparently).
   *Recommended: `PyJWKClient`. It already does what we need; refresh on
   `kid` miss handles rotation.*

3. **Audience claim**: oauth2-proxy strips `aud`-vs-`azp` weirdness for
   itself. For the API we accept tokens whose `azp == iot-web` *or*
   `aud` contains `iot-api` (when 0014's audience-mapper is added — see
   below). *Recommended: validate `azp == "iot-web"` for v1 and skip
   `aud`. Add an explicit Keycloak audience-mapper later if a separate
   service principal arrives.*

4. **Existing tests**: how do we obtain a valid signed JWT in the
   integration suite without making test runs slow?
   *Recommended: at fixture setup, call Keycloak's token endpoint once
   per role using direct-access-grants (resource-owner password). Cache
   the four tokens for the whole pytest session. Requires enabling
   `directAccessGrantsEnabled: true` on the `iot-web` client (currently
   `false`). Tiny realm change.*

5. **401 body**: stick with FastAPI's default (`{"detail": "..."}`) or
   emit a structured `{"error": "...", "code": "..."}`?
   *Recommended: keep the FastAPI default. Aligns with everything else
   in the API.*

6. **Scope of changes to existing tests**: rewrite each module to send
   tokens, or apply tokens transparently via a session-scoped
   `httpx.Client` fixture?
   *Recommended: transparent fixture. Existing tests get an admin token
   by default; new role-matrix tests live in a new
   `tests/test_rbac.py`. Keeps the diff localized.*
