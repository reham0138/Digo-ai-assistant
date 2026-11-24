import asyncio

import pytest

from services.delivery_assistant.app.agents.delivery_agent import (
    DELIVERY_SYSTEM_PROMPT,
)
from services.delivery_assistant.app.api.routes import chat as chat_module
from services.delivery_assistant.app.integrations.nutrition_search import (
    _DuckDuckGoLiteParser,
)


def test_delivery_prompt_uses_semantic_tool_selection_policy():
    prompt = DELIVERY_SYSTEM_PROMPT.lower()

    assert "understand the meaning and intent" in prompt
    assert "fixed keyword lists to decide whether a request belongs" in prompt
    assert "nutrition_search tool" in prompt
    assert "MUST select nutrition_search" in prompt
    assert "Do NOT answer these questions from model knowledge" in prompt


def test_nutrition_search_is_registered_as_a_delivery_tool():
    tools = chat_module._build_tools()

    assert "nutrition_search" in tools.names

    definition = tools.definitions()[0]
    assert definition["name"] == "nutrition_search"
    assert definition["parameters"]["required"] == ["query"]
    assert definition["parameters"]["additionalProperties"] is False
    assert "REQUIRED" in definition["description"]
    assert "Arabic or English" in definition["description"]


def test_nutrition_search_tool_executes_and_formats_sources(monkeypatch):
    class FakeNutritionSearch:
        async def search(self, query: str) -> list[dict[str, str]]:
            assert query == "chicken shawarma"
            return [{
                "title": "Chicken shawarma nutrition",
                "snippet": "About 400 calories per serving.",
                "url": "https://example.com/shawarma",
            }]

    monkeypatch.setattr(chat_module, "NutritionSearch", FakeNutritionSearch)
    tools = chat_module._build_tools()

    result = asyncio.run(
        tools.execute("nutrition_search", {"query": "chicken shawarma"})
    )

    assert "About 400 calories per serving." in result
    assert "https://example.com/shawarma" in result
    assert "estimates" in result.lower()


def test_nutrition_search_rejects_invalid_arguments():
    tools = chat_module._build_tools()

    with pytest.raises(ValueError):
        asyncio.run(
            tools.execute(
                "nutrition_search",
                {"query": "chicken shawarma", "unexpected": True},
            )
        )


def test_search_parser_extracts_title_snippet_and_source():
    html = """
    <tr><td><a class="result-link" href="https://example.com/nutrition">
    Chicken nutrition facts</a></td></tr>
    <tr><td class="result-snippet">About 250 calories per serving.</td></tr>
    """
    parser = _DuckDuckGoLiteParser()
    parser.feed(html)

    assert parser.results == [{
        "url": "https://example.com/nutrition",
        "title": "Chicken nutrition facts",
        "snippet": "About 250 calories per serving.",
    }]
