from fastapi import FastAPI
from routes import test, dummy

app = FastAPI(
    title="API de la Plataforma IoT",
    description="API para gestionar dispositivos IoT utilizando FastAPI",
    version="1.0.0"
)

app.include_router(test.router, prefix="/test", tags=["test"])
app.include_router(dummy.router, prefix="/dummy", tags=["dummy"])   