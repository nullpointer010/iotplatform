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

    # MQTT bridge (ticket 0018). Set mqtt_enabled=false to skip starting
    # the in-process broker subscriber (e.g. when running offline tests).
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_username: str = "bridge"
    mqtt_password: str = "change-me-bridge"
    mqtt_max_payload_bytes: int = 65536
    mqtt_enabled: bool = True

    # Live ingest simulator (ticket 0019b). Off by default; enabled
    # in compose so `make up` shows live data without extra steps.
    simulator_enabled: bool = False
    simulator_interval_seconds: int = 10
    simulator_api_base_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
