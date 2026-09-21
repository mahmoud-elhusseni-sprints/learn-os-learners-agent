from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.app.schemas.agent_response import EmployerResponse


class ConversationCreate(BaseModel):
    pass


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    sender_role: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_role: str
    content: str
    timestamp: datetime


class ChatResponse(BaseModel):
    message: MessageResponse
    response: EmployerResponse


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)
    learner_name_or_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
