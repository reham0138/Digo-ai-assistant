import pytest

from shared.ai_core.tools.tool_registry import ToolRegistry
from shared.ai_core.validation.response_validator import validate_text_response


def test_tool_registry_registers_and_resolves_tool():
    registry = ToolRegistry()
    handler = lambda value: value.upper()
    registry.register("uppercase", handler)
    assert registry.get("uppercase")("hello") == "HELLO"
    assert registry.names == ("uppercase",)


def test_tool_registry_rejects_duplicate_names():
    registry = ToolRegistry()
    registry.register("lookup", lambda: None)
    with pytest.raises(ValueError):
        registry.register("lookup", lambda: None)


def test_tool_registry_rejects_unknown_arguments():
    registry = ToolRegistry()
    registry.register(
        "lookup",
        lambda name: name,
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    )
    with pytest.raises(ValueError, match="unsupported"):
        pytest.importorskip("asyncio").run(registry.execute("lookup", {"name": "x", "sql": "DROP"}))


def test_response_validator_rejects_empty_text():
    with pytest.raises(ValueError):
        validate_text_response("  ")
