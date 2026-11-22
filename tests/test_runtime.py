import pytest

from shared.ai_core.conversation.models import ChatMessage
from shared.ai_core.runtime import AssistantRuntime


class FakeOllamaClient:
    def __init__(self, response: str = "A test response") -> None:
        self.response = response
        self.last_prompt = None
        self.last_system = None

    async def generate(self, prompt: str, system: str | None = None) -> str:
        self.last_prompt = prompt
        self.last_system = system
        return self.response


def test_runtime_uses_service_prompt_and_formats_history():
    client = FakeOllamaClient()
    runtime = AssistantRuntime(client, "You are a test assistant.")

    answer = pytest.importorskip("asyncio").run(
        runtime.respond(
            "What next?",
            [ChatMessage(role="user", content="Hello"), ChatMessage(role="assistant", content="Hi")],
        )
    )

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
        [
            ChatMessage(role="user", content="Old message"),
            ChatMessage(role="assistant", content="Recent message"),
        ],
    )

    assert "Old message" not in prompt
    assert "Recent message" in prompt


def test_runtime_rejects_empty_system_prompt():
    with pytest.raises(ValueError):
        AssistantRuntime(FakeOllamaClient(), "  ")


def test_runtime_rejects_empty_user_message():
    runtime = AssistantRuntime(FakeOllamaClient(), "Prompt")
    with pytest.raises(ValueError):
        pytest.importorskip("asyncio").run(runtime.respond("  "))
