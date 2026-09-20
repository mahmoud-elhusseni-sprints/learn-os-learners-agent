from sqlalchemy.orm import Session

from src.app.models.conversation import ConversationSession
from src.app.models.message import Message
from src.app.repositories import conversation_repository, user_repository
from src.app.schemas.agent_response import EmployerResponse
from src.app.services.agent_orchestration import (
    AgentOrchestrationAdapter,
    AgentTimeoutError,
    AgentUpstreamError,
)


def create_conversation(
    db: Session,
    user_id: int,
    current_user_id: int,
) -> ConversationSession:
    if user_id != current_user_id:
        raise ValueError("Conversation not found")

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
    current_user_id: int,
) -> list[ConversationSession]:
    if user_id != current_user_id:
        raise ValueError("Conversation not found")

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
    current_user_id: int,
) -> Message:
    conversation = conversation_repository.get_conversation_by_id(
        db,
        conversation_id,
    )

    if conversation is None:
        raise ValueError("Conversation not found")

    if conversation.user_id != current_user_id:
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
    current_user_id: int,
) -> list[Message]:
    conversation = conversation_repository.get_conversation_by_id(
        db,
        conversation_id,
    )

    if conversation is None:
        raise ValueError("Conversation not found")

    if conversation.user_id != current_user_id:
        raise ValueError("Conversation not found")

    return conversation_repository.get_conversation_messages(
        db,
        conversation_id,
    )


def chat(
    db: Session,
    conversation_id: int,
    current_user_id: int,
    content: str,
    learner_name_or_id: str | None = None,
    agent_adapter: AgentOrchestrationAdapter | None = None,
) -> tuple[Message, EmployerResponse]:
    conversation = conversation_repository.get_conversation_by_id(
        db,
        conversation_id,
    )

    if conversation is None:
        raise ValueError("Conversation not found")

    if conversation.user_id != current_user_id:
        raise ValueError("Conversation not found")

    try:
        history = conversation_repository.get_conversation_history(
            db,
            conversation_id,
        )

        conversation_repository.create_message(
            db,
            conversation_id,
            "user",
            content,
            commit=False,
        )

        adapter = agent_adapter or AgentOrchestrationAdapter()

        answer = adapter.respond(
            content,
            history=history,
            learner_name_or_id=learner_name_or_id,
        )

        assistant_message = conversation_repository.create_message(
            db,
            conversation_id,
            "assistant",
            answer.markdown,
            commit=False,
        )

        db.commit()
        db.refresh(assistant_message)

        return assistant_message, answer

    except (AgentTimeoutError, AgentUpstreamError):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise