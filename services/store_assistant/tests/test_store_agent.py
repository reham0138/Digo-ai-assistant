import asyncio

import pytest

from services.store_assistant.app.agents.store_agent import STORE_SYSTEM_PROMPT
from services.store_assistant.app.api.routes import chat as chat_module
from services.store_assistant.app.schemas.chat import StoreChatRequest


@pytest.mark.parametrize(
    "message",
    [
        "Help me choose a laptop for university",
        "شو الفرق بين SSD و HDD؟",
        "Is OLED better than IPS?",
        "Recommend a phone for photography",
    ],
)
def test_general_product_advice_is_sent_to_model(message, monkeypatch):
    _assert_message_reaches_model(message, monkeypatch)


@pytest.mark.parametrize(
    "message",
    [
        "Do you have gaming laptops?",
        "How much is this item?",
        "Is this product available in Latakia?",
        "Are there any discounts on headphones?",
        "عندكم لابتوبات؟",
        "قديش باقي من هالمنتج؟",
    ],
)
def test_live_store_data_questions_are_sent_to_model(message, monkeypatch):
    _assert_message_reaches_model(message, monkeypatch)


@pytest.mark.parametrize(
    "message",
    [
        "Tell me a joke",
        "What's the weather today?",
        "Explain Python decorators",
        "Who won the football match?",
    ],
)
def test_out_of_scope_questions_are_sent_to_model_for_policy_handling(
    message, monkeypatch
):
    _assert_message_reaches_model(message, monkeypatch)


def _assert_message_reaches_model(message, monkeypatch):
    calls = {}

    class FakeOllamaClient:
        def __init__(self, **kwargs):
            calls["client_kwargs"] = kwargs

    class FakeAssistantRuntime:
        def __init__(self, client, system_prompt):
            calls["system_prompt"] = system_prompt

        async def respond(self, received_message, history):
            calls["message"] = received_message
            calls["history"] = history
            return "mocked response"

    monkeypatch.setattr(chat_module, "OllamaClient", FakeOllamaClient)
    monkeypatch.setattr(chat_module, "AssistantRuntime", FakeAssistantRuntime)

    request = StoreChatRequest(message=message)
    response = asyncio.run(chat_module.chat(request))

    assert response.message == "mocked response"
    assert calls["message"] == message
    assert calls["system_prompt"] == STORE_SYSTEM_PROMPT


def test_system_prompt_distinguishes_advice_from_live_store_facts():
    prompt = STORE_SYSTEM_PROMPT.casefold()

    assert "general product education is in scope" in prompt
    assert "require live store data" in prompt
    assert "do not invent product names, prices, discounts, stock" in prompt
    assert "live store data is not connected yet" in prompt
    assert "outside this scope" in prompt
