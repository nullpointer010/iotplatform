import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import make_engine, make_sessionmaker
from app.middleware import RequestIdMiddleware
from app.orion import OrionClient
from app.quantumleap import QuantumLeapClient
from app.routes import devices, health, maintenance, manuals, me, telemetry


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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app = FastAPI(
        title="CropDataSpace IoT Platform API",
        description="REST API for the CropDataSpace IoT platform.",
        version="0.1.0",
        lifespan=lifespan,
    )
    origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    errors_log = logging.getLogger("app.errors")

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", "-")
        errors_log.exception(
            "Unhandled error %s %s rid=%s", request.method, request.url.path, rid,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": rid},
            headers={"X-Request-ID": rid},
        )

    app.include_router(health.router)
    app.include_router(me.router, prefix=settings.api_prefix)
    app.include_router(devices.router, prefix=settings.api_prefix)
    app.include_router(telemetry.router, prefix=settings.api_prefix)
    app.include_router(maintenance.router, prefix=settings.api_prefix)
    app.include_router(manuals.router, prefix=settings.api_prefix)
    return app


app = create_app()
