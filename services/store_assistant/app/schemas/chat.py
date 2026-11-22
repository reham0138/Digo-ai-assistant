from pydantic import BaseModel, Field


class StoreChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    branch_id: str | None = None
    conversation_id: str | None = None


class StoreChatResponse(BaseModel):
    message: str
    recommendations: list[dict] = Field(default_factory=list)
