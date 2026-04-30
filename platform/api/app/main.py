from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import get_settings
from app.orion import OrionClient
from app.routes import devices, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as client:
        app.state.orion = OrionClient(settings, client)
        yield


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
    return app


app = create_app()
