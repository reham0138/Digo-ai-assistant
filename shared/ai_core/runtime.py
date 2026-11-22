"""Reusable runtime for prompt-configured, single-turn assistant responses."""
from __future__ import annotations

from collections.abc import Sequence

from shared.ai_core.conversation.models import ChatMessage
from shared.ai_core.llm.ollama_client import OllamaClient
from shared.ai_core.validation.response_validator import validate_text_response


class AssistantRuntime:
    """Run an assistant with a service-owned system prompt and chat history.

    The runtime deliberately knows nothing about store or delivery business
    rules. Each service supplies its own prompt and trusted tools separately.
    """

    def __init__(
        self,
        client: OllamaClient,
        system_prompt: str,
        max_history_messages: int = 12,
    ) -> None:
        if not system_prompt.strip():
            raise ValueError("system_prompt must not be empty")
        if max_history_messages < 0:
            raise ValueError("max_history_messages must be zero or greater")

        self.client = client
        self.system_prompt = system_prompt.strip()
        self.max_history_messages = max_history_messages

    def build_prompt(
        self,
        message: str,
        history: Sequence[ChatMessage] = (),
    ) -> str:
        recent_history = history[-self.max_history_messages :] if self.max_history_messages else ()
        lines = [
            f"{item.role.capitalize()}: {item.content}"
            for item in recent_history
        ]
        lines.append(f"User: {message.strip()}")
        lines.append("Assistant:")
        return "Conversation:\n" + "\n".join(lines)

    async def respond(
        self,
        message: str,
        history: Sequence[ChatMessage] = (),
    ) -> str:
        if not message or not message.strip():
            raise ValueError("message must not be empty")

        prompt = self.build_prompt(message, history)
        response = await self.client.generate(prompt, system=self.system_prompt)
        return validate_text_response(response)
