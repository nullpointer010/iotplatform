from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI

from app.config import get_settings
from app.db import make_engine, make_sessionmaker
from app.orion import OrionClient
from app.quantumleap import QuantumLeapClient
from app.routes import devices, health, maintenance, telemetry


def _run_migrations(database_url: str) -> None:
    cfg_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = AlembicConfig(str(cfg_path))
    cfg.set_main_option("script_location", str(cfg_path.parent / "alembic"))
    # env.py reads DATABASE_URL from env, not from alembic.ini.
    import os
    os.environ["DATABASE_URL"] = database_url
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _run_migrations(settings.database_url)

    engine = make_engine(settings)
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)

    async with httpx.AsyncClient(timeout=10.0) as client:
        app.state.orion = OrionClient(settings, client)
        app.state.ql = QuantumLeapClient(settings, client)
        try:
            yield
        finally:
            await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CropDataSpace IoT Platform API",
        description="REST API for the CropDataSpace IoT platform.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(devices.router, prefix=settings.api_prefix)
    app.include_router(telemetry.router, prefix=settings.api_prefix)
    app.include_router(maintenance.router, prefix=settings.api_prefix)
    return app


app = create_app()
