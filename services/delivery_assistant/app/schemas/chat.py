from pydantic import BaseModel, Field


class DeliveryChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class DeliveryChatResponse(BaseModel):
    message: str
    restaurants: list[dict] = Field(default_factory=list)
