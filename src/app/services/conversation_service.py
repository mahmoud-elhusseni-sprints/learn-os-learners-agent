from sqlalchemy.orm import Session

from src.app.repositories import conversation_repository
from src.app.repositories import user_repository


def create_conversation(
    db: Session,
    user_id: int,
):
    user = user_repository.get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise ValueError("User not found")

    return conversation_repository.create_conversation(
        db,
        user_id,
    )


def get_user_conversations(
    db: Session,
    user_id: int,
):
    user = user_repository.get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise ValueError("User not found")

    return conversation_repository.get_user_conversations(
        db,
        user_id,
    )


def add_message(
    db: Session,
    conversation_id: int,
    sender_role: str,
    content: str,
):
    conversation = conversation_repository.get_conversation_by_id(
        db,
        conversation_id,
    )

    if conversation is None:
        raise ValueError("Conversation not found")

    return conversation_repository.create_message(
        db,
        conversation_id,
        sender_role,
        content,
    )


def get_messages(
    db: Session,
    conversation_id: int,
):
    conversation = conversation_repository.get_conversation_by_id(
        db,
        conversation_id,
    )

    if conversation is None:
        raise ValueError("Conversation not found")

    return conversation_repository.get_conversation_messages(
        db,
        conversation_id,
    )