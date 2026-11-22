"""Chat endpoint for the Store Assistant."""
import httpx
from fastapi import APIRouter, HTTPException

from services.store_assistant.app.agents.store_agent import (
    STORE_SYSTEM_PROMPT,
    is_live_store_data_query,
    is_store_related,
)
from services.store_assistant.app.config import settings
from services.store_assistant.app.schemas.chat import StoreChatRequest, StoreChatResponse
from shared.ai_core.llm.ollama_client import OllamaClient
from shared.ai_core.runtime import AssistantRuntime

router = APIRouter()

OUT_OF_SCOPE_REPLY = (
    "I'm the store shopping assistant. I can help with products, product "
    "selection, prices, stock, branches, and store orders. I can't help with "
    "that topic, but feel free to ask me a store-related question."
)


LIVE_STORE_DATA_UNAVAILABLE_REPLY = (
    "I can't check live product listings, prices, stock, discounts, or branch "
    "availability yet because the store backend is not connected. "
    "I won't guess or make up that information."
)


@router.post("/chat", response_model=StoreChatResponse)
async def chat(request: StoreChatRequest) -> StoreChatResponse:
    if not is_store_related(request.message):
        return StoreChatResponse(message=OUT_OF_SCOPE_REPLY)

    if is_live_store_data_query(request.message):
        return StoreChatResponse(message=LIVE_STORE_DATA_UNAVAILABLE_REPLY)

    client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    runtime = AssistantRuntime(client, STORE_SYSTEM_PROMPT)

    try:
        answer = await runtime.respond(request.message, request.history)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="The configured Ollama service is unavailable.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return StoreChatResponse(message=answer)
