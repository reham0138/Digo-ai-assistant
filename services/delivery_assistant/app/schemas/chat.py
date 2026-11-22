from pydantic import BaseModel, Field

from shared.ai_core.conversation.models import ChatMessage


class DeliveryChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=128)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class DeliveryChatResponse(BaseModel):
    message: str
    restaurants: list[dict] = Field(default_factory=list)
