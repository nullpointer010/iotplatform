# Journal — 0014 backend JWT + RBAC

## Decisions

- **`pyjwt[crypto]` over `python-jose` / `authlib`.** Smaller surface,
  actively maintained, no transitive deprecation warnings.
- **`PyJWKClient` for JWKS.** Built-in caching with kid-miss refresh;
  no homegrown TTL logic. The cached client is keyed on the URL via a
  module-level `lru_cache`, so a settings reload still picks up a new
  URL transparently.
- **`verify_aud=False` + explicit `azp` check.** Keycloak's default access
  token for `iot-web` carries `aud: ["account"]`, not the client id. We
  validate `azp == iot-web` instead. This is documented in `auth.py`.
- **`admin` is a global override.** Implemented as
  `allowed | {"admin"}` inside `require_roles` — every endpoint that
  declares any constraint silently allows admins. Cleaner than scattering
  `"admin"` through 16 dependency calls.
- **Per-route `dependencies=[Depends(require_roles(...))]`** rather than
  a router-level dependency. Different verbs on the same path need
  different roles (e.g. `GET /devices` is viewer, `POST /devices` is
  operator); router-level wouldn't fit.
- **`directAccessGrantsEnabled` on `iot-web`.** Realm-import file flipped
  to `true` so the test fixture can fetch tokens with the password grant.
  Acceptable for a dev realm; note in review.md flags it for production
  hardening.
- **Test fixture is transparent.** The session-scoped `api` fixture
  attaches an admin token by default → the 80 pre-existing tests pass
  with zero changes. RBAC negative cases live in a new
  `tests/test_rbac.py` and create their own per-call clients with
  the token they want to exercise.

## Bugs hit

- **Double `@pytest.fixture` decorator on `api`.** Stale leftover from a
  copy-paste; pytest 8 errors hard. Trivial fix.
- **`/healthz` is mounted without the `/api/v1` prefix.** First version
  of `test_health_is_public` hit `/api/v1/healthz` and 404'd; the route
  lives at `/healthz`. Adjusted the test.

## Lessons

- When adding auth across many routes, prefer one explicit decorator per
  route over hidden global magic — a future reader sees the policy on
  the line that owns the verb. The boilerplate is worth it.
- Realm changes that affect tokens are not subtle: every change requires
  dropping the keycloak-db volume because `--import-realm` only seeds
  empty databases. Document the procedure once (`make down` + `docker
  volume rm compose_keycloak_db_data` + `make up`); we re-used it from
  0013b without surprises.
- The "admin always allowed" rule is one of the rare cases where
  implicit behaviour pays off: it eliminates a pile of repetitive
  `"admin"` strings in route declarations and prevents the
  forgotten-admin foot-gun.

## Verification

- `make test` — 95/95 green (was 80; +15 new RBAC tests).
- `tests/test_rbac.py` exercises 401/403/200 on `devices`, `state`,
  `operation-types`, `maintenance/log`, plus public `healthz`.
- `cd web && npm test` 2/2; `tsc --noEmit` clean; `next build` 7/7.
- Manual web smoke: login still works, `/devices` renders, no 401.
