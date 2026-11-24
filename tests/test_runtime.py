import json

import pytest

from shared.ai_core.conversation.models import ChatMessage
from shared.ai_core.runtime import AssistantRuntime
from shared.ai_core.tools.tool_registry import ToolRegistry


class FakeOllamaClient:
    def __init__(self, response: str = "A test response") -> None:
        self.response = response
        self.last_prompt = None
        self.last_system = None
        self.last_schema = None

    async def generate(self, prompt: str, system: str | None = None) -> str:
        self.last_prompt = prompt
        self.last_system = system
        return self.response

    async def generate_structured(
        self, prompt: str, schema: dict, system: str | None = None
    ) -> str:
        self.last_prompt = prompt
        self.last_system = system
        self.last_schema = schema
        return self.response


def run(coro):
    return pytest.importorskip("asyncio").run(coro)


def test_runtime_uses_service_prompt_and_formats_history():
    client = FakeOllamaClient()
    runtime = AssistantRuntime(client, "You are a test assistant.")

    answer = run(runtime.respond(
        "What next?",
        [ChatMessage(role="user", content="Hello"), ChatMessage(role="assistant", content="Hi")],
    ))

    assert answer == "A test response"
    assert client.last_system == "You are a test assistant."
    assert "User: Hello" in client.last_prompt
    assert "Assistant: Hi" in client.last_prompt
    assert client.last_prompt.endswith("User: What next?\nAssistant:")


def test_runtime_limits_history_to_most_recent_messages():
    client = FakeOllamaClient()
    runtime = AssistantRuntime(client, "Prompt", max_history_messages=1)
    prompt = runtime.build_prompt(
        "Current",
        [ChatMessage(role="user", content="Old message"),
         ChatMessage(role="assistant", content="Recent message")],
    )
    assert "Old message" not in prompt
    assert "Recent message" in prompt


def test_runtime_rejects_empty_system_prompt():
    with pytest.raises(ValueError):
        AssistantRuntime(FakeOllamaClient(), "  ")


def test_runtime_rejects_empty_user_message():
    runtime = AssistantRuntime(FakeOllamaClient(), "Prompt")
    with pytest.raises(ValueError):
        run(runtime.respond("  "))


def test_runtime_selects_and_executes_only_registered_tool():
    client = FakeOllamaClient(json.dumps({
        "action": "use_tool",
        "response": "",
        "tool_name": "lookup_stock",
        "arguments": {"product": "laptop"},
    }))
    tools = ToolRegistry()
    tools.register(
        "lookup_stock",
        lambda product: f"Trusted stock result for {product}",
        description="Look up product stock.",
        parameters={
            "type": "object",
            "properties": {"product": {"type": "string"}},
            "required": ["product"],
            "additionalProperties": False,
        },
    )
    runtime = AssistantRuntime(client, "Store assistant.", tools=tools)

    assert run(runtime.respond("Is the laptop in stock?")) == "Trusted stock result for laptop"
    assert '"name": "lookup_stock"' in client.last_prompt


def test_runtime_returns_model_answer_without_executing_tool():
    client = FakeOllamaClient(json.dumps({
        "action": "respond",
        "response": "Here is general advice.",
        "tool_name": "",
        "arguments": {},
    }))
    tools = ToolRegistry()
    tools.register("lookup", lambda: "should not run")
    runtime = AssistantRuntime(client, "Assistant.", tools=tools)

    assert run(runtime.respond("Explain SSD vs HDD")) == "Here is general advice."


def test_runtime_rejects_unregistered_tool():
    client = FakeOllamaClient(json.dumps({
        "action": "use_tool",
        "response": "",
        "tool_name": "delete_everything",
        "arguments": {},
    }))
    tools = ToolRegistry()
    tools.register("safe_lookup", lambda: "safe result")
    runtime = AssistantRuntime(client, "Assistant.", tools=tools)

    with pytest.raises(RuntimeError, match="rejected"):
        run(runtime.respond("Do something"))
