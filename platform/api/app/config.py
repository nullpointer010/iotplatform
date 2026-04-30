from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    orion_url: str = "http://orion:1026"
    fiware_service: str = "iot"
    fiware_servicepath: str = "/"
    api_prefix: str = "/api/v1"
    quantumleap_url: str = "http://quantumleap:8668"
    database_url: str = "postgresql+asyncpg://iot_user:iot_password@postgres:5432/iot_database"
    cors_allow_origins: str = ""

    # Keycloak / RBAC (ticket 0014). The issuer must match exactly the
    # `iss` claim in tokens (use the browser-facing URL). The JWKS URL
    # is fetched server-side, so it points at the in-network hostname.
    keycloak_issuer: str = "http://localhost:8081/realms/iot-platform"
    keycloak_jwks_url: str = (
        "http://keycloak:8080/realms/iot-platform/protocol/openid-connect/certs"
    )
    keycloak_client_id: str = "iot-web"
    auth_disabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
