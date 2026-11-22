"""Basic guardrails for assistant text responses.

Structured recommendations will receive stricter validation against trusted
catalogue/API records in the relevant service integration layer.
"""


def validate_text_response(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Assistant response must be a non-empty string.")
    return value.strip()
