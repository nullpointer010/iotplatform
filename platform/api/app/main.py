from fastapi import FastAPI

from app.routes import health

app = FastAPI(
    title="CropDataSpace IoT Platform API",
    description="REST API for the CropDataSpace IoT platform.",
    version="0.1.0",
)

app.include_router(health.router)
