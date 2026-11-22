"""Chat endpoint for the Store Assistant."""
import httpx
from fastapi import APIRouter, HTTPException

from services.store_assistant.app.agents.store_agent import STORE_SYSTEM_PROMPT
from services.store_assistant.app.config import settings
from services.store_assistant.app.schemas.chat import StoreChatRequest, StoreChatResponse
from shared.ai_core.llm.ollama_client import OllamaClient
from shared.ai_core.runtime import AssistantRuntime

router = APIRouter()


@router.post("/chat", response_model=StoreChatResponse)
async def chat(request: StoreChatRequest) -> StoreChatResponse:
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
