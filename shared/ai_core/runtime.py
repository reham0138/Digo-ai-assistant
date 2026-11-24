"""Reusable runtime for prompt-configured assistants and scoped tools."""
from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

from shared.ai_core.conversation.models import ChatMessage
from shared.ai_core.llm.ollama_client import OllamaClient
from shared.ai_core.tools.tool_registry import ToolRegistry
from shared.ai_core.validation.response_validator import validate_text_response

logger = logging.getLogger(__name__)


def _build_plan_schema(tool_names: Sequence[str]) -> dict[str, Any]:
    """Constrain tool selection to tools explicitly registered by this service."""
    return {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["respond", "use_tool"]},
            "response": {"type": "string"},
            "tool_name": {"type": "string", "enum": ["", *tool_names]},
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
            "You are an action router for this assistant. Read the user's complete "
            "meaning, not isolated words. Decide whether the request needs a fact "
            "or operation that one of the available tools provides.\n"
            "- If a tool can retrieve the specific information requested, you MUST "
            "choose action=use_tool. Do not answer from memory, guess, or claim the "
            "information is unavailable before trying that tool.\n"
            "- Choose action=respond only when no listed tool is relevant, or when "
            "the user asks for general explanation/advice rather than retrieved facts.\n"
            "- Understand paraphrases and the language used by the user. Do not "
            "require the user to use the tool's exact wording.\n"
            "- Use only a listed tool and provide arguments matching its schema.\n\n"
            f"{conversation}\n\n"
            f"Available tools and their purposes: {tool_catalog}\n\n"
            "Return the required JSON object. For action=respond, put the complete "
            "user-facing answer in response, set tool_name to an empty string, and "
            "arguments to an empty object. For action=use_tool, set tool_name and "
            "arguments, and set response to an empty string."
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
            schema=_build_plan_schema(self.tools.names),
            system=self.system_prompt,
        )
        try:
            plan = json.loads(raw_plan)
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Ollama returned an invalid assistant action plan.") from exc

        if not isinstance(plan, dict) or plan.get("action") not in {"respond", "use_tool"}:
            raise RuntimeError("Ollama returned an unsupported assistant action.")
        if plan["action"] == "respond":
            logger.info("Assistant action selected: respond")
            try:
                return validate_text_response(plan.get("response"))
            except ValueError as exc:
                raise RuntimeError("Ollama returned an empty assistant response.") from exc

        tool_name = plan.get("tool_name")
        arguments = plan.get("arguments")
        if not isinstance(tool_name, str) or not tool_name or not isinstance(arguments, dict):
            raise RuntimeError("Ollama returned invalid tool-call details.")
        logger.info("Assistant action selected: use_tool (%s)", tool_name)
        try:
            return await self.tools.execute(tool_name, arguments)
        except (KeyError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Assistant tool call was rejected: {exc}") from exc
