"""Chat endpoint for the Delivery Assistant."""
import httpx
from fastapi import APIRouter, HTTPException

from services.delivery_assistant.app.agents.delivery_agent import (
    DELIVERY_SYSTEM_PROMPT,
    is_delivery_related,
    is_nutrition_query,
)
from services.delivery_assistant.app.config import settings
from services.delivery_assistant.app.integrations.nutrition_search import (
    NutritionSearch,
    NutritionSearchError,
)
from services.delivery_assistant.app.schemas.chat import DeliveryChatRequest, DeliveryChatResponse
from shared.ai_core.llm.ollama_client import OllamaClient
from shared.ai_core.runtime import AssistantRuntime

router = APIRouter()

OUT_OF_SCOPE_REPLY = (
    "I'm the food ordering and delivery assistant. I can help with restaurants, "
    "meals, menus, delivery, pickup, food orders, and food nutrition questions."
)

NO_NUTRITION_RESULTS_REPLY = (
    "I couldn't find reliable web results for that food's nutrition information. "
    "Try specifying the dish and portion size."
)


def _format_nutrition_results(food_query: str, results: list[dict[str, str]]) -> str:
    """Present retrieved snippets and their sources without LLM-generated facts."""
    lines = [
        f"Nutrition information found for: {food_query}",
        "These are web-search estimates, not exact values. Calories vary with "
        "portion size, ingredients, and preparation.",
    ]
    for index, result in enumerate(results, start=1):
        lines.append(
            f"{index}. {result['title']}\n"
            f"{result['snippet']}\n"
            f"Source: {result['url']}"
        )
    return "\n\n".join(lines)


@router.post("/chat", response_model=DeliveryChatResponse)
async def chat(request: DeliveryChatRequest) -> DeliveryChatResponse:
    if not is_delivery_related(request.message):
        return DeliveryChatResponse(message=OUT_OF_SCOPE_REPLY)

    # Nutrition facts are fetched from the web and returned with their sources.
    # The LLM is deliberately bypassed so it cannot invent numeric values.
    if is_nutrition_query(request.message):
        try:
            results = await NutritionSearch().search(request.message)
        except NutritionSearchError as exc:
            raise HTTPException(
                status_code=503,
                detail="Nutrition web search is temporarily unavailable.",
            ) from exc

        if not results:
            return DeliveryChatResponse(message=NO_NUTRITION_RESULTS_REPLY)
        return DeliveryChatResponse(
            message=_format_nutrition_results(request.message, results)
        )

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
