from pydantic import BaseModel, Field

from shared.ai_core.conversation.models import ChatMessage


class StoreChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    branch_id: str | None = None
    conversation_id: str | None = Field(default=None, max_length=128)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class StoreChatResponse(BaseModel):
    message: str
    recommendations: list[dict] = Field(default_factory=list)
