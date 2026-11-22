from fastapi import FastAPI
from services.delivery_assistant.app.api.routes.health import router as health_router

app = FastAPI(title="Delivery Assistant", version="0.1.0")
app.include_router(health_router)
