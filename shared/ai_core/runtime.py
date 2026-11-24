"""Reusable runtime for prompt-configured assistants and scoped tools."""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from shared.ai_core.conversation.models import ChatMessage
from shared.ai_core.llm.ollama_client import OllamaClient
from shared.ai_core.tools.tool_registry import ToolRegistry
from shared.ai_core.validation.response_validator import validate_text_response


_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["respond", "use_tool"]},
        "response": {"type": "string"},
        "tool_name": {"type": "string"},
        "arguments": {"type": "object"},
    },
    "required": ["action", "response", "tool_name", "arguments"],
    "additionalProperties": False,
}


class AssistantRuntime:
    """Run an assistant with a service-owned prompt and explicitly granted tools.

    When tools are registered, the model produces a constrained action plan.
    The runtime validates the selected tool and its arguments before execution.
    Tool output is returned as-is; a tool must format and source its own result.
    """

    def __init__(
        self,
        client: OllamaClient,
        system_prompt: str,
        max_history_messages: int = 12,
        tools: ToolRegistry | None = None,
    ) -> None:
        if not system_prompt.strip():
            raise ValueError("system_prompt must not be empty")
        if max_history_messages < 0:
            raise ValueError("max_history_messages must be zero or greater")

        self.client = client
        self.system_prompt = system_prompt.strip()
        self.max_history_messages = max_history_messages
        self.tools = tools or ToolRegistry()

    def build_prompt(
        self,
        message: str,
        history: Sequence[ChatMessage] = (),
    ) -> str:
        recent_history = history[-self.max_history_messages :] if self.max_history_messages else ()
        lines = [f"{item.role.capitalize()}: {item.content}" for item in recent_history]
        lines.append(f"User: {message.strip()}")
        lines.append("Assistant:")
        return "Conversation:\n" + "\n".join(lines)

    def _build_action_prompt(self, conversation: str) -> str:
        tool_catalog = json.dumps(self.tools.definitions(), ensure_ascii=False)
        return (
            f"{conversation}\n\n"
            "Choose exactly one action. Use a tool only when the user's request "
            "requires information or an operation that the listed tool provides. "
            "Otherwise answer the user directly. Never invent a tool or arguments.\n"
            f"Available tools: {tool_catalog}\n"
            "Return the required JSON object. For action=respond, put the complete "
            "user-facing answer in response and leave tool_name empty and arguments "
            "as an empty object. For action=use_tool, set tool_name and arguments, "
            "and leave response empty."
        )

    async def respond(
        self,
        message: str,
        history: Sequence[ChatMessage] = (),
    ) -> str:
        if not message or not message.strip():
            raise ValueError("message must not be empty")

        prompt = self.build_prompt(message, history)
        if not self.tools.names:
            response = await self.client.generate(prompt, system=self.system_prompt)
            return validate_text_response(response)

        raw_plan = await self.client.generate_structured(
            self._build_action_prompt(prompt),
            schema=_PLAN_SCHEMA,
            system=self.system_prompt,
        )
        try:
            plan = json.loads(raw_plan)
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Ollama returned an invalid assistant action plan.") from exc

        if not isinstance(plan, dict) or plan.get("action") not in {"respond", "use_tool"}:
            raise RuntimeError("Ollama returned an unsupported assistant action.")
        if plan["action"] == "respond":
            try:
                return validate_text_response(plan.get("response"))
            except ValueError as exc:
                raise RuntimeError("Ollama returned an empty assistant response.") from exc

        tool_name = plan.get("tool_name")
        arguments = plan.get("arguments")
        if not isinstance(tool_name, str) or not isinstance(arguments, dict):
            raise RuntimeError("Ollama returned invalid tool-call details.")
        try:
            return await self.tools.execute(tool_name, arguments)
        except (KeyError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Assistant tool call was rejected: {exc}") from exc
