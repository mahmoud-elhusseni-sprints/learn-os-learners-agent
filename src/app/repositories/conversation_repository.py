import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.conversation import ConversationSession
from src.app.models.message import Message


def create_conversation(
    db: Session,
    user_id: int,
) -> ConversationSession:
    conversation = ConversationSession(
        user_id=user_id,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def get_conversation_by_id(
    db: Session,
    conversation_id: int,
) -> ConversationSession | None:
    return db.get(ConversationSession, conversation_id)


def get_user_conversations(
    db: Session,
    user_id: int,
) -> list[ConversationSession]:
    statement = (
        select(ConversationSession)
        .where(ConversationSession.user_id == user_id)
        .order_by(ConversationSession.created_at)
    )

    return list(db.scalars(statement).all())


def create_message(
    db: Session,
    conversation_id: int,
    sender_role: str,
    content: str,
    artifacts: list[dict] | None = None,
    commit: bool = True,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        sender_role=sender_role,
        content=content,
        artifacts=json.dumps(artifacts) if artifacts else None,
    )

    db.add(message)

    if commit:
        db.commit()
        db.refresh(message)
    else:
        db.flush()

    return message


def get_conversation_messages(
    db: Session,
    conversation_id: int,
) -> list[Message]:
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp, Message.id)
    )

    return list(db.scalars(statement).all())


def get_conversation_history(
    db: Session,
    conversation_id: int,
) -> list[dict[str, str]]:
    messages = get_conversation_messages(db, conversation_id)

    return [
        {
            "role": message.sender_role,
            "content": message.content,
        }
        for message in messages
    ]
