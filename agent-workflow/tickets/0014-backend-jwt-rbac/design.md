# Design — 0014 backend JWT + RBAC

## New module: `app/auth.py`

```python
from functools import lru_cache
from fastapi import Depends, HTTPException, Request, status
import jwt                              # pyjwt
from jwt import PyJWKClient

from app.config import get_settings


class Principal:
    def __init__(self, sub: str, username: str, roles: set[str]):
        self.sub, self.username, self.roles = sub, username, roles


@lru_cache
def _jwks_client() -> PyJWKClient:
    return PyJWKClient(get_settings().keycloak_jwks_url, cache_keys=True)


def _decode(token: str) -> dict:
    s = get_settings()
    signing_key = _jwks_client().get_signing_key_from_jwt(token).key
    return jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        issuer=s.keycloak_issuer,
        options={"require": ["exp", "iat", "iss", "azp", "sub"],
                 "verify_aud": False},
    )


def get_principal(request: Request) -> Principal:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = auth.split(None, 1)[1]
    try:
        claims = _decode(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    if claims.get("azp") != get_settings().keycloak_client_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid azp")

    roles = set(((claims.get("realm_access") or {}).get("roles") or []))
    return Principal(claims["sub"], claims.get("preferred_username", ""), roles)


def require_roles(*allowed: str):
    """admin always allowed; otherwise the token must carry one of `allowed`."""
    allowed_set = set(allowed) | {"admin"}

    def _dep(p: Principal = Depends(get_principal)) -> Principal:
        if p.roles.isdisjoint(allowed_set):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return p

    return _dep
```

`PyJWKClient` caches keys and re-fetches on `kid` miss → key rotation works.

## Settings additions (`app/config.py`)

```
keycloak_issuer: str       = "http://localhost:8081/realms/iot-platform"
keycloak_jwks_url: str     = "http://keycloak:8080/realms/iot-platform/protocol/openid-connect/certs"
keycloak_client_id: str    = "iot-web"
auth_disabled: bool        = False
```

`auth_disabled` is a dev-only escape hatch; defaults False so production
is locked down. Tests do **not** rely on it — they use real tokens.

## Compose / env

`platform/.env.example` + `platform/.env`:

```
# ─── API auth (ticket 0014) ───
KEYCLOAK_ISSUER=http://localhost:8081/realms/iot-platform
KEYCLOAK_JWKS_URL=http://keycloak:8080/realms/iot-platform/protocol/openid-connect/certs
KEYCLOAK_CLIENT_ID=iot-web
```

`docker-compose.api.yml` injects them into the `iot-api` service via
`environment:`.

## Routes — applied policy

Each route gains a `Depends(require_roles(...))` matching the matrix in
`requirements.md`. Concretely:

- `devices.py`
  - `POST /devices`           — `require_roles("operator")`
  - `GET  /devices`           — `require_roles("viewer", "operator", "maintenance_manager")`
  - `GET  /devices/{id}`      — same as list
  - `PATCH /devices/{id}`     — `require_roles("operator")`
  - `DELETE /devices/{id}`    — `require_roles()` (admin-only via the
    "admin always allowed" rule; explicit empty set documents intent)
- `telemetry.py`
  - `GET /devices/{id}/telemetry`, `/state` — viewer/operator/manager
- `maintenance.py`
  - `GET  /maintenance/operation-types`     — viewer/operator/manager
  - mutating `operation-types`              — `require_roles("maintenance_manager")`
  - `GET  /maintenance/log…`                — viewer/operator/manager
  - `POST/PATCH /maintenance/log…`          — `require_roles("operator", "maintenance_manager")`
  - `DELETE /maintenance/log/{id}`          — `require_roles("maintenance_manager")`
- `health.py` — **untouched, public.**

Application strategy: a single line at the top of each route file
declares a module-level `dependencies=[]` is _not_ enough because the
required roles differ per route. We add one `Depends` per route. Mild
boilerplate — explicit and readable.

## Realm change

`iot-web` client gains `directAccessGrantsEnabled: true` so tests can
fetch tokens via the resource-owner password grant. Realm import file
already has `confidential` access type which supports it. One-line JSON
edit; requires re-importing the realm (drop `compose_keycloak_db_data`
once, same as 0013b).

## Tests

### `tests/_tokens.py` (new helper)

A session-scoped helper that fetches one token per role from Keycloak
once and caches them. `_get_token("admin")` returns a string usable as
`Authorization: Bearer …`.

### `conftest.py` changes

```python
@pytest.fixture(scope="session")
def tokens() -> dict[str, str]:
    return {role: _fetch(role) for role in
            ("viewer", "operator", "manager", "admin")}

@pytest.fixture(scope="session")
def api(tokens) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=API_BASE, timeout=30.0,
                      headers={"Authorization": f"Bearer {tokens['admin']}"}) as c:
        yield c
```

The default `api` fixture sends an admin token — every existing test
keeps passing without per-test changes. New test files can construct an
`httpx.Client` with a different role header for negative cases.

### `tests/test_rbac.py` (new)

Five representative endpoints × {no token (401), wrong role (403),
right role (200)} = ~15 assertions. Covers devices, telemetry, state,
operation-types, maintenance/log.

## Web

No code change needed. oauth2-proxy already forwards the Bearer token
(`PASS_AUTHORIZATION_HEADER=true` from 0013). The browser's relative
`/api/v1/...` calls (set up in 0013b) carry the cookie; the proxy
strips the cookie, attaches the token, forwards to the API.

Manual smoke: load `/devices` after login → list renders without
errors. After 0014, removing the token makes the API say 401, which we
verify with a direct curl from outside the proxy.

## Risks

- **Test boot-time**: fetching 4 tokens at session start adds ~1s.
  Acceptable.
- **JWKS unavailable at first request after a fresh boot**: `iot-api`
  starts before `keycloak` is healthy. The settings only matter on
  first authed call; `PyJWKClient` retries internally. We add
  `depends_on: keycloak: { condition: service_healthy }` to `iot-api`
  to make the dev experience predictable.
- **`directAccessGrantsEnabled`**: enables resource-owner password grant
  on `iot-web`. Acceptable for dev-only realm; flagged in the journal
  as something to disable for production realms.
- **`verify_aud=False`**: Keycloak access tokens for `iot-web` carry
  `aud: ["account"]`, not `iot-web`. We compensate by validating
  `azp == iot-web` explicitly. Documented.
