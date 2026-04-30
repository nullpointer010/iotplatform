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


@lru_cache
def get_settings() -> Settings:
    return Settings()
