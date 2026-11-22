"""Chat endpoint for the Delivery Assistant."""
import httpx
from fastapi import APIRouter, HTTPException

from services.delivery_assistant.app.agents.delivery_agent import DELIVERY_SYSTEM_PROMPT
from services.delivery_assistant.app.config import settings
from services.delivery_assistant.app.schemas.chat import DeliveryChatRequest, DeliveryChatResponse
from shared.ai_core.llm.ollama_client import OllamaClient
from shared.ai_core.runtime import AssistantRuntime

router = APIRouter()


@router.post("/chat", response_model=DeliveryChatResponse)
async def chat(request: DeliveryChatRequest) -> DeliveryChatResponse:
    client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    runtime = AssistantRuntime(client, DELIVERY_SYSTEM_PROMPT)

    try:
        answer = await runtime.respond(request.message, request.history)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="The configured Ollama service is unavailable.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return DeliveryChatResponse(message=answer)
