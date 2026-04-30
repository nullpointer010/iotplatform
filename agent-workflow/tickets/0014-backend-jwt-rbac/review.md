# Self-review — 0014 backend JWT + RBAC

## ACs

1. ✓ Unauthenticated requests to data routes → 401 (verified by
   `test_devices_list_requires_auth`, `test_state_requires_auth`,
   `test_log_list_requires_auth`).
2. ✓ Insufficient role → 403 (verified by
   `test_devices_create_forbidden_for_viewer`,
   `test_devices_delete_forbidden_for_operator`,
   `test_op_types_create_forbidden_for_operator`,
   `test_log_delete_forbidden_for_operator`).
3. ✓ Right role → 200 (`viewer` lists devices,
   `operator` creates a device, `manager` creates an operation-type,
   `admin` deletes a device).
4. ✓ `/healthz` stays public.
5. ✓ JWKS validated via `PyJWKClient` (caches keys, refreshes on
   `kid` miss → key rotation works without an API restart).
6. ✓ Test coverage for one representative endpoint per resource.
7. ✓ `make test` green (95/95). Existing tests unchanged thanks to the
   transparent admin-token fixture.
8. ✓ Web still works end-to-end: oauth2-proxy forwards the bearer token
   (`PASS_AUTHORIZATION_HEADER=true` from 0013), `/devices` loads.

## Risks / follow-ups

- `directAccessGrantsEnabled=true` on `iot-web` is a dev convenience
  for token fetching from the test fixture. Disable for any production
  realm (use a service-account client there instead).
- Test fixture re-fetches 4 tokens per pytest session (~1s). If session
  speed becomes a concern we can build raw JWTs from a Keycloak signing
  key, but it isn't worth the complexity yet.
- `auth_disabled=True` is a debugging escape hatch only. It is **not**
  a feature flag for production; the code path returns an admin-shaped
  Principal unconditionally. Documented in `auth.py`.
- The `aud` claim is intentionally not validated (Keycloak emits
  `aud: ["account"]` by default for `iot-web`). If a separate API
  client appears, we wire a Keycloak audience-mapper and flip
  `verify_aud=True` with an explicit `audience="iot-api"`.

## Security

- Every data route now demands a valid token; the API can no longer be
  hit anonymously even from inside `iot-net`.
- Token validation enforces signature (RS256), issuer, expiry,
  presence of `azp/sub/iat/exp`, and `azp == iot-web`. Replay attacks
  bounded by `exp`.
- `require_roles()` evaluates against `realm_access.roles` from the
  token. Tampered tokens fail signature check before this is reached.

## Diff scope

- `platform/api/requirements.txt` — `pyjwt[crypto]==2.10.1`.
- `platform/api/app/auth.py` — new module (Principal, get_principal,
  require_roles).
- `platform/api/app/config.py` — Keycloak settings + `auth_disabled`.
- `platform/api/app/routes/{devices,telemetry,maintenance}.py` — one
  `Depends(require_roles(...))` per endpoint per the matrix.
- `platform/compose/docker-compose.api.yml` — KEYCLOAK_* env injected;
  `depends_on` adds `keycloak`.
- `platform/config/keycloak/realm-iot.json` —
  `iot-web.directAccessGrantsEnabled: true`.
- `platform/api/tests/conftest.py` — token fixture; admin-token wrapper
  on the session `api` client.
- `platform/api/tests/test_rbac.py` — new (15 tests).
- Ticket files (requirements/design/tasks/journal/review/status) and
  roadmap.
