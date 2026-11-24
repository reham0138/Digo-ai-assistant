"""Chat endpoint for the Delivery Assistant."""
import httpx
from fastapi import APIRouter, HTTPException

from services.delivery_assistant.app.agents.delivery_agent import DELIVERY_SYSTEM_PROMPT
from services.delivery_assistant.app.config import settings
from services.delivery_assistant.app.integrations.nutrition_search import (
    NutritionSearch,
    NutritionSearchError,
)
from services.delivery_assistant.app.schemas.chat import DeliveryChatRequest, DeliveryChatResponse
from shared.ai_core.llm.ollama_client import OllamaClient
from shared.ai_core.runtime import AssistantRuntime
from shared.ai_core.tools.tool_registry import ToolRegistry

router = APIRouter()

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


def _build_tools() -> ToolRegistry:
    tools = ToolRegistry()

    async def nutrition_search(query: str) -> str:
        results = await NutritionSearch().search(query)
        if not results:
            return NO_NUTRITION_RESULTS_REPLY
        return _format_nutrition_results(query, results)

    tools.register(
        "nutrition_search",
        nutrition_search,
        description=(
            "REQUIRED for any request asking for calories, energy, macros, "
            "protein, carbohydrates, fat, or nutritional facts about a named "
            "food, ingredient, meal, or dish. Interpret paraphrases and Arabic "
            "or English requests semantically; do not require exact wording. "
            "Examples: 'calories in chicken shawarma', 'is hummus high in "
            "protein?', or 'what are the macros in this meal?'. Search the web "
            "and return attributed snippets with source URLs. Do not use for "
            "general explanations of nutrients."
        ),
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "minLength": 2}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )
    return tools


@router.post("/chat", response_model=DeliveryChatResponse)
async def chat(request: DeliveryChatRequest) -> DeliveryChatResponse:
    client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    runtime = AssistantRuntime(
        client,
        DELIVERY_SYSTEM_PROMPT,
        tools=_build_tools(),
    )

    try:
        answer = await runtime.respond(request.message, request.history)
    except NutritionSearchError as exc:
        raise HTTPException(
            status_code=503,
            detail="Nutrition web search is temporarily unavailable.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="The configured Ollama service is unavailable.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return DeliveryChatResponse(message=answer)
