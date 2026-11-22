from fastapi import FastAPI

from services.store_assistant.app.api.routes.chat import router as chat_router
from services.store_assistant.app.api.routes.health import router as health_router

app = FastAPI(title="Store Assistant", version="0.2.0")
app.include_router(health_router)
app.include_router(chat_router)
