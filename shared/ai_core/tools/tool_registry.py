"""Explicit registry for tools available to one assistant instance."""
from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any


class ToolRegistry:
    """Stores only the tools explicitly granted to a service runtime."""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        *,
        description: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> None:
        if not name or not name.replace("_", "").isalnum():
            raise ValueError("Tool names must contain only letters, numbers, and underscores.")
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = {
            "handler": handler,
            "description": description.strip(),
            "parameters": parameters or {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        }

    def get(self, name: str) -> Callable[..., Any]:
        try:
            return self._tools[name]["handler"]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def definitions(self) -> list[dict[str, Any]]:
        """Return model-facing descriptions, never executable handlers."""
        return [
            {
                "name": name,
                "description": item["description"],
                "parameters": item["parameters"],
            }
            for name, item in self._tools.items()
        ]

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object.")
        item = self._tools.get(name)
        if item is None:
            raise KeyError(f"Unknown tool: {name}")

        schema = item["parameters"]
        allowed = set(schema.get("properties", {}))
        required = set(schema.get("required", []))
        if schema.get("additionalProperties") is False and set(arguments) - allowed:
            raise ValueError("Tool arguments contain unsupported fields.")
        if required - set(arguments):
            raise ValueError("Tool arguments are missing required fields.")

        result = item["handler"](**arguments)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, str) or not result.strip():
            raise ValueError("Tool handlers must return a non-empty string.")
        return result.strip()
