from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.app.api.dependencies.auth import get_current_user
from src.app.database.connection import get_db
from src.app.models.conversation import ConversationSession
from src.app.models.message import Message
from src.app.models.user import User
from src.app.schemas.conversation import (
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from src.app.services import conversation_service

router = APIRouter(
    tags=["Conversations"],
)


@router.post(
    "/users/{user_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationSession:
    try:
        return conversation_service.create_conversation(
            db,
            user_id,
            current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/users/{user_id}/conversations",
    response_model=list[ConversationResponse],
)
def get_user_conversations(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationSession]:
    try:
        return conversation_service.get_user_conversations(
            db,
            user_id,
            current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    conversation_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Message:
    try:
        return conversation_service.add_message(
            db,
            conversation_id,
            message_data.sender_role,
            message_data.content,
            current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Message]:
    try:
        return conversation_service.get_messages(
            db,
            conversation_id,
            current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc