"""JWT validation + RBAC for the API (ticket 0014).

Tokens are issued by Keycloak via oauth2-proxy. We validate signature
against Keycloak's JWKS (cached, with kid-miss refresh handling key
rotation), check `iss` and `azp`, then surface a `Principal` with
realm roles.

`require_roles(*allowed)` is the per-route gate. `admin` is implicitly
allowed everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt import PyJWKClient

from app.config import Settings, get_settings


@dataclass
class Principal:
    sub: str
    username: str
    roles: frozenset[str]


@lru_cache
def _jwks_client_for(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True)


def _decode(token: str, settings: Settings) -> dict:
    signing_key = _jwks_client_for(settings.keycloak_jwks_url).get_signing_key_from_jwt(token).key
    return jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        issuer=settings.keycloak_issuer,
        options={
            "require": ["exp", "iat", "iss", "azp", "sub"],
            # Keycloak access tokens for `iot-web` carry `aud: ["account"]`.
            # We validate authorisation via `azp` instead (checked below).
            "verify_aud": False,
        },
    )


def get_principal(request: Request) -> Principal:
    settings = get_settings()
    if settings.auth_disabled:
        return Principal(sub="dev", username="dev", roles=frozenset({"admin"}))

    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = auth.split(None, 1)[1]
    try:
        claims = _decode(token, settings)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}") from exc

    if claims.get("azp") != settings.keycloak_client_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid azp")

    realm_access = claims.get("realm_access") or {}
    roles = frozenset(realm_access.get("roles") or [])
    return Principal(
        sub=claims["sub"],
        username=claims.get("preferred_username", ""),
        roles=roles,
    )


def require_roles(*allowed: str):
    """Dependency factory: passes if the principal has any role in `allowed`,
    or the `admin` role (implicit superuser)."""

    allowed_set = frozenset(allowed) | {"admin"}

    def _dep(p: Principal = Depends(get_principal)) -> Principal:
        if p.roles.isdisjoint(allowed_set):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return p

    return _dep
